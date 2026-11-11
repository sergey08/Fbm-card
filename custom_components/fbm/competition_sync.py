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
                     *, fetch_rosters: bool = True, expected_competition: dict | None = None) -> dict:
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
    # First check official membership in the selected phase/group.
    # This must precede player-detail verification; only those official
    # member IDs are eligible to corroborate a season.
    standings = await client.async_team_standings(team_id)
    rows = standings.get("clasificacion") if type(standings) is dict else None
    if type(rows) is not list or len(rows) < 2 or len(rows) > MAX_TEAMS:
        raise ValueError("Clasificación de grupo no válida")
    team_ids = []
    for row in rows:
        tid = row.get("id") if type(row) is dict else None
        if type(tid) is not str or not tid.strip() or len(tid) > 512 or tid in team_ids:
            raise ValueError("Identificador de equipo duplicado o inválido")
        team_ids.append(tid)
    if team_id not in team_ids:
        raise ValueError("El equipo no figura en la clasificación del grupo")
    # If an explicit refresh targets the saved competition, a moved phase
    # or group is a transition, not an unselected group.
    if expected_competition is not None and (
            type(expected_competition) is not dict
            or identity["phase_id"] != expected_competition.get("phase_id")
            or identity["group_id"] != expected_competition.get("group_id")):
        return {"status": "competition_changed", "saved": False}
    # The official search season label is stored when the user follows a
    # competition. Refreshes reuse that consented identity; FBM's group
    # endpoint does not provide another season ID. Never infer an ID from
    # player details and never auto-follow an unselected competition.
    group = await asyncio.to_thread(
        archive.selected_for_team, team_id,
        identity["phase_id"], identity["group_id"])
    if group is None:
        return {"status": "not_followed", "saved": False}
    # Detect phase/season/group transitions before ANY fixture or roster
    # download, not after archiving under a possibly different identity.
    if expected_competition is not None:
        required = ("season_id", "phase_id", "group_id")
        if (type(expected_competition) is not dict
                or any(type(expected_competition.get(k)) is not str
                       for k in required)
                or any(group[k] != expected_competition[k] for k in required)):
            return {"status": "competition_changed", "saved": False}

    # Only the native competition manager may grant opt-in. A direct
    # WebSocket sync call cannot silently enroll a new group or download
    # player rosters from a competition the user has not selected.
    if not await asyncio.to_thread(archive.is_followed, group):
        return {"status": "not_followed", "saved": False}

    fixtures = await client.async_team_schedule(team_id, start, end)
    if type(fixtures) is not dict or type(fixtures.get("partidos")) is not list:
        raise ValueError("Calendario oficial no válido")

    # Opt-in incremental mode: new officially finished matches imply that
    # rosters may have changed. Only then load all team rosters again.
    # Missing initial rosters are also backfilled; no player stats are fetched
    # here and no unselected competition can be enrolled.
    fixture_results_changed = False
    if fetch_rosters == "on_change":
        previous = await asyncio.to_thread(
            archive.latest, group, "fixtures")
        def finished_scores(document):
            rows = (document or {}).get("partidos", [])
            return {
                item["id"]: (item["marcador"]["local"],
                             item["marcador"]["visitante"])
                for item in rows if type(item) is dict
                and type(item.get("id")) is str
                and item.get("estado") == "finished"
                and type(item.get("marcador")) is dict
                and type(item["marcador"].get("local")) is int
                and type(item["marcador"].get("visitante")) is int
            }
        old = finished_scores((previous or {}).get("payload"))
        new = finished_scores(fixtures)
        fixture_results_changed = old != new
        missing_roster = any(
            not await asyncio.to_thread(
                archive.latest, group, "roster", tid)
            for tid in team_ids
        )
        fetch_rosters = fixture_results_changed or missing_roster
    elif type(fetch_rosters) is not bool:
        raise ValueError("Modo de plantillas no válido")

    # Fetch rosters sequentially, not concurrently, and keep a simple delay.
    # This limits pressure on the unofficial access to FBM.
    rosters = {}
    failed_rosters = []
    team_names = {row['id']: row.get('equipo') for row in rows}
    if fetch_rosters:
        for tid in team_ids:
            # The user may have stopped following while the earlier remote
            # calls were running. Do not request another player's record.
            if not await asyncio.to_thread(archive.is_followed, group):
                return {"status": "not_followed", "saved": False}
            try:
                response = await client.async_team_roster(tid)
                if type(response) is not dict or type(response.get("jugadores")) is not list:
                    raise ValueError("Plantilla no válida")
                rosters[tid] = response
            except Exception:
                name = team_names[tid]
                failed_rosters.append(name.strip()[:120] if isinstance(name, str) else "")
            await asyncio.sleep(0.3)

    # The explicit follow can be revoked during the requests. Check again
    # immediately before persistence to honor a stop-following action.
    if not await asyncio.to_thread(archive.is_followed, group):
        return {"status": "not_followed", "saved": False}
    # Each snapshot is transactional; an individual roster failure preserves
    # the last-good record rather than erasing it.
    results = {}
    for source, subject, data in (
            ("standings", "", standings), ("fixtures", "", fixtures),
            *((("roster", tid, response) for tid, response in rosters.items()))):
        results[source + (":" + subject if subject else "")] = await asyncio.to_thread(
            archive.record, group, source, data, subject=subject)
    # Backfill readable names for pre-existing beta archives after successful
    # sync; never re-follow a group that an admin has deactivated.
    source_team = next(
        (row.get("equipo") for row in rows if row.get("id") == team_id), "")
    competition_name = ""
    search = getattr(client, "async_search_teams", None)
    if callable(search) and isinstance(source_team, str) and 0 < len(source_team) <= 100:
        followed = await asyncio.to_thread(archive.followed_with_anchor)
        saved = next((item for item in followed if all(
            item[key] == group[key] for key in ("season_id", "phase_id", "group_id")
        )), None)
        if saved is not None and not saved.get("competition_name"):
            try:
                candidates = await search(source_team)
                labels = {item["categoria"].strip() for item in candidates
                          if item.get("id") == team_id
                          and isinstance(item.get("categoria"), str)
                          and 0 < len(item["categoria"].strip()) <= 120}
                if len(labels) == 1:
                    competition_name = labels.pop()
            except Exception:
                # The display label is optional; the archive remains usable.
                pass
    await asyncio.to_thread(archive.update_display, group, {
        "team_name": source_team if type(source_team) is str else "",
        "competition_name": competition_name,
        "phase_name": identity.get("phase_name") or "",
        "group_name": identity.get("group_name") or "",
    })
    return {
        "status": "partial" if failed_rosters else "ok",
        "saved": True, "team_count": len(team_ids),
        "fixture_count": len(fixtures["partidos"]),
        "rosters_saved": len(rosters), "roster_errors": len(failed_rosters),
        "failed_roster_names": [name for name in failed_rosters if name],
        "records_written": sum(bool(v) for v in results.values()),
        "fixture_results_changed": fixture_results_changed,
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
    if any(type(row) is not dict or type(row.get("id")) is not str
           or type(row.get("equipo")) is not str for row in rows):
        raise ValueError("Participantes de grupo no válidos")
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
