"""Explicit, bounded synchronization of a verified FBM competition group.

Never infer seasons, silently follow groups or schedule background requests.
The client uses the existing authenticated FBM adapter and normalized results.
"""
from __future__ import annotations

import asyncio
from datetime import date


MAX_TEAMS = 20
MAX_RANGE_DAYS = 125


async def sync_group(client, archive, team_id: str, start: date, end: date,
                     *, fetch_rosters: bool = True) -> dict:
    """Fetch all opponents of the selected team's *official current group*.

    Called only on explicit administrator request. If season identity has
    not been verified, return a safe blocker and do not write or download
    player-level records.
    """
    if type(team_id) is not str or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no válido")
    if (type(start) is not date or type(end) is not date or start > end
            or (end - start).days > MAX_RANGE_DAYS):
        raise ValueError("Periodo no válido")
    identity = await client.async_team_group_identity(team_id)
    for field in ("phase_id", "group_id"):
        value = identity.get(field)
        if type(value) is not str or not value.strip():
            raise ValueError("No hay grupo oficial verificado")
    if identity.get("season_verified") is not True:
        return {
            "status": "season_unverified",
            "group_verified": True,
            "season_evidence_status": identity.get("season_evidence_status", "none"),
            "saved": False,
        }
    group = {
        "season_id": identity["season_id"], "phase_id": identity["phase_id"],
        "group_id": identity["group_id"], "season_verified": True,
    }
    standings = await client.async_team_standings(team_id)
    rows = standings.get("clasificacion") if type(standings) is dict else None
    if type(rows) is not list or not rows or len(rows) > MAX_TEAMS:
        raise ValueError("Clasificación de grupo no válida o demasiado grande")
    team_ids = []
    for row in rows:
        tid = row.get("id") if type(row) is dict else None
        if type(tid) is not str or not tid.strip() or len(tid) > 512 or tid in team_ids:
            raise ValueError("Identificador de equipo duplicado o inválido")
        team_ids.append(tid)
    fixtures = await client.async_team_schedule(team_id, start, end)
    if type(fixtures) is not dict or type(fixtures.get("partidos")) is not list:
        raise ValueError("Calendario oficial no válido")

    # Fetch rosters sequentially, not concurrently, and keep a simple delay.
    # This limits pressure on the unofficial access to FBM.
    rosters = {}
    errors = 0
    if fetch_rosters:
        for tid in team_ids:
            try:
                response = await client.async_team_roster(tid)
                if type(response) is not dict or type(response.get("jugadores")) is not list:
                    raise ValueError("Plantilla no válida")
                rosters[tid] = response
            except Exception:
                errors += 1
            await asyncio.sleep(0.3)

    # Atomicity per snapshot: no partial invalid DTO is written. Last-good
    # snapshots remain available when an individual roster request fails.
    await asyncio.to_thread(archive.follow, group)
    results = {}
    for source, subject, data in (
            ("standings", "", standings), ("fixtures", "", fixtures),
            *((("roster", tid, response) for tid, response in rosters.items()))):
        results[source + (":" + subject if subject else "")] = await asyncio.to_thread(
            archive.record, group, source, data, subject=subject)
    return {
        "status": "partial" if errors else "ok",
        "saved": True, "team_count": len(team_ids),
        "fixture_count": len(fixtures["partidos"]),
        "rosters_saved": len(rosters), "roster_errors": errors,
        "records_written": sum(bool(v) for v in results.values()),
        "competition": {k: group[k] for k in ("season_id", "phase_id", "group_id")},
    }


async def preview_group(client, team_id: str, start: date, end: date) -> dict:
    """Read-only official group preview; does not fetch players or persist data."""
    if type(team_id) is not str or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no válido")
    if (type(start) is not date or type(end) is not date or start > end
            or (end - start).days > MAX_RANGE_DAYS):
        raise ValueError("Periodo no válido")
    identity = await client.async_team_group_identity(team_id)
    if not identity.get("group_id") or not identity.get("phase_id"):
        raise ValueError("Grupo oficial no disponible")
    standings = await client.async_team_standings(team_id)
    fixtures = await client.async_team_schedule(team_id, start, end)
    rows = standings.get("clasificacion") if type(standings) is dict else None
    matches = fixtures.get("partidos") if type(fixtures) is dict else None
    if (type(rows) is not list or len(rows) > MAX_TEAMS
            or type(matches) is not list or len(matches) > 500):
        raise ValueError("Respuesta oficial demasiado grande")
    return {
        "status": "preview",
        "persisted": False,
        "group_id": identity["group_id"],
        "phase_id": identity["phase_id"],
        "season_verified": identity.get("season_verified") is True,
        "season_evidence_status": identity.get("season_evidence_status", "none"),
        "group_name": identity.get("group_name"),
        "phase_name": identity.get("phase_name"),
        "team_count": len(rows),
        "match_count": len(matches),
        "teams": [{"id": row["id"], "name": row["equipo"]}
                  for row in rows if type(row) is dict
                  and type(row.get("id")) is str and type(row.get("equipo")) is str],
    }
