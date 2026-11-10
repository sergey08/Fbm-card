"""Bounded, explicit synchronization of FBM individual sporting match stats.

Only players on an already archived roster for a followed competition
can be queried. No player photos, profiles or raw DTOs are persisted.
"""
from __future__ import annotations

import asyncio


async def sync_player_stats_batch(client, archive, competition: dict,
                                  team_id: str, offset: int = 0,
                                  limit: int = 5) -> dict:
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
    saved, errors, missing = 0, 0, 0
    for player in subset:
        if not await asyncio.to_thread(archive.is_followed, competition):
            return {"status": "not_followed", "saved": saved,
                    "processed": saved + errors + missing}
        player_id = player.get("id") if type(player) is dict else None
        if type(player_id) is not str or not player_id or len(player_id) > 512:
            errors += 1
            continue
        try:
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
            "processed": len(subset), "saved": saved, "errors": errors,
            "players_without_match_data": missing,
            "next_offset": offset + len(subset) if offset + len(subset) < len(players) else None,
            "roster_size": len(players)}
