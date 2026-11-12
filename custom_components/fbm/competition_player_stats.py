"""Bounded, explicit synchronization of FBM individual sporting match stats.

Only players on an already archived roster for a followed competition
can be queried. No player photos, profiles or raw DTOs are persisted.
"""
from __future__ import annotations

import asyncio


async def sync_player_stats_batch(client, archive, competition: dict,
                                  team_id: str, offset: int = 0,
                                  limit: int = 5,
                                  force_recheck: bool = False) -> dict:
    if type(force_recheck) is not bool:
        raise ValueError("Revalidación no válida")
    if type(team_id) is not str or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo inválido")
    if (type(offset) is not int or offset < 0
            or type(limit) is not int or not 1 <= limit <= 5):
        raise ValueError("Lote fuera de los límites")
    if not await asyncio.to_thread(archive.is_followed, competition):
        return {"status": "not_followed", "saved": 0}
    roster = await asyncio.to_thread(archive.latest, competition, "roster", team_id)
    if not roster:
        return {"status": "no_roster", "saved": 0}
    players = roster["payload"].get("jugadores")
    if type(players) is not list or len(players) > 100:
        raise ValueError("Plantilla inválida")
    subset = players[offset:offset + limit]
    saved, errors, missing, skipped = 0, 0, 0, 0
    for player in subset:
        if not await asyncio.to_thread(archive.is_followed, competition):
            return {"status": "not_followed", "saved": saved,
                    "processed": saved + errors + missing}
        player_id = player.get("id") if type(player) is dict else None
        if type(player_id) is not str or not player_id or len(player_id) > 512:
            errors += 1
            continue
        try:
            # Only query newly played fixtures: the official roster already
            # includes how many appearances the player has made.  An existing
            # complete snapshot with that many unique matches needs no new
            # remote request. An explicit admin refresh remains available.
            existing = await asyncio.to_thread(
                archive.latest, competition, "player_stats", player_id)
            cached_games = (existing or {}).get("payload", {}).get("partidos")
            appearances = player.get("partidos_jugados")
            # A zero-appearance player cannot have official match stats.
            # The FBM endpoint returns an error-like payload for these
            # roster entries, so do not request them or count a sync error.
            # Once the roster reports a first appearance, the normal
            # incremental mechanism fetches their individual statistics.
            if type(appearances) is int and appearances == 0:
                skipped += 1
                continue
            if (not force_recheck
                    and type(appearances) is int and 0 <= appearances <= 200
                    and type(cached_games) is list
                    and len({m.get("id_partido") for m in cached_games
                             if type(m) is dict and type(m.get("id_partido")) is str})
                        >= appearances
                    and all(type(m) is dict and type(m.get("puntos")) is int
                            for m in cached_games)
                    and appearances > 0):
                skipped += 1
                continue
            stats = await client.async_player_statistics(player_id, team_id)
            if (type(stats) is not dict or stats.get("jugador") != player_id
                    or stats.get("equipo") != team_id):
                raise ValueError("Estadísticas no asociadas al jugador y equipo")
            matches = stats.get("partidos", {}).get("partidos")
            globales = stats.get("globales", {}).get("estadisticas")
            if type(matches) is not list or type(globales) is not dict:
                raise ValueError("No hay estadísticas oficiales verificadas")
            # Archive.recheck follows in the same DB transaction as the write.
            was_written = await asyncio.to_thread(
                archive.record, competition, "player_stats",
                {"partidos": matches, "globales": globales},
                subject=player_id)
            saved += int(was_written)
            if not matches:
                missing += 1
        except Exception:
            errors += 1
        await asyncio.sleep(0.5)
    return {"status": "partial" if errors else "ok",
            "processed": len(subset), "saved": saved, "skipped_unchanged": skipped,
            "errors": errors,
            "players_without_match_data": missing,
            "next_offset": offset + len(subset) if offset + len(subset) < len(players) else None,
            "roster_size": len(players)}
