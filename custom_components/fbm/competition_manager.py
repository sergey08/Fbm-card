"""Resolve FBM groups from official search labels and phase/group identifiers.

The FBM team search provides a visible season ("26/27"), while the group
endpoint does not return a separate season ID. Do not invent one or query
minor players merely to follow a competition.
"""
from __future__ import annotations

import re

_SEASON = re.compile(r"^(\d{2})/(\d{2})$")


def official_season_label(label: str) -> str:
    """Accept only an unambiguous consecutive-season label from FBM search."""
    if type(label) is not str:
        raise ValueError("Temporada oficial no válida")
    value = label.strip()
    match = _SEASON.fullmatch(value)
    if not match or (int(match[1]) + 1) % 100 != int(match[2]):
        raise ValueError("Temporada oficial no válida")
    return value


async def identify_competition(client, team_id: str, season_label: str | None = None) -> dict:
    if type(team_id) is not str or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no válido")
    if season_label is None:
        # Older clients can still perform a non-persistent preview; following
        # requires the official season string from the selected search result.
        return {"status": "season_unverified", "team_count": 0}
    season = official_season_label(season_label)
    identity = await client.async_team_group_identity(team_id)
    phase_id, group_id = identity.get("phase_id"), identity.get("group_id")
    if (type(phase_id) is not str or not phase_id
            or type(group_id) is not str or not group_id):
        raise ValueError("Grupo no verificado")
    standings = await client.async_team_standings(team_id)
    rows = standings.get("clasificacion") if type(standings) is dict else None
    if type(rows) is not list or not 2 <= len(rows) <= 20:
        raise ValueError("Clasificación incompleta o demasiado grande")
    ids = []
    for row in rows:
        team = row.get("id") if type(row) is dict else None
        if type(team) is not str or not team or len(team) > 512 or team in ids:
            raise ValueError("Identificador oficial de equipo inválido")
        ids.append(team)
    if team_id not in ids:
        raise ValueError("El equipo no pertenece al grupo")
    return {"status": "verified", "team_count": len(ids),
            "season_id": season, "phase_id": phase_id, "group_id": group_id,
            "phase_name": identity.get("phase_name") or "Fase",
            "group_name": identity.get("group_name") or "Grupo",
            "season_verified": True, "season_source": "official_team_search"}


async def competition_season_diagnostic(client, team_id: str) -> dict:
    """Optional legacy cross-team diagnostic, no player data or IDs returned."""
    identity = await client.async_team_group_identity(team_id)
    standings = await client.async_team_standings(team_id)
    rows = standings.get("clasificacion") if type(standings) is dict else None
    if not identity.get("phase_id") or not identity.get("group_id") or type(rows) is not list:
        raise ValueError("Grupo no disponible")
    ids = [row["id"] for row in rows if type(row) is dict
           and type(row.get("id")) is str]
    if len(ids) < 2:
        raise ValueError("Grupo incompleto")
    evidence = await client.async_verify_group_season(ids)
    return {"status": "verified" if evidence.get("season_verified") is True else "season_unverified",
            "group_verified": True, "team_count": len(ids),
            "season_match_verified": evidence.get("season_verified") is True}


def group_selection(competition: dict) -> dict:
    if type(competition) is not dict or competition.get("status") != "verified":
        raise ValueError("Competición sin temporada oficial")
    return {key: competition[key] for key in (
        "season_id", "phase_id", "group_id", "season_verified")}
