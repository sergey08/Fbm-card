"""Safe competition-selection operations for the Home Assistant options flow.

Selecting a team follows the entire verified official season/phase/group.
No player records or photos are persisted by selection.
"""
from __future__ import annotations


async def identify_competition(client, team_id: str) -> dict:
    if type(team_id) is not str or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no válido")
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
    evidence = (identity if identity.get("season_verified") is True
                else await client.async_verify_group_season(ids))
    season = evidence.get("season_id")
    if evidence.get("season_verified") is not True or type(season) is not str or not season:
        return {"status": "season_unverified", "team_count": len(ids),
                "phase_id": phase_id, "group_id": group_id}
    return {"status": "verified", "team_count": len(ids),
            "season_id": season, "phase_id": phase_id, "group_id": group_id,
            "season_verified": True}


def group_selection(competition: dict) -> dict:
    """A verified identity suitable for CompetitionArchive.follow/unfollow."""
    if type(competition) is not dict or competition.get("status") != "verified":
        raise ValueError("No se puede seguir una competición sin verificar")
    return {key: competition[key] for key in (
        "season_id", "phase_id", "group_id", "season_verified")}
