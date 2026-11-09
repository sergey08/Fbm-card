"""Bridge from the official FBM client to the opt-in group coordinator.

Fail closed until an independently verified official season identifier exists.
Never infer season from a display name, year, team id, or the current date.
"""
from __future__ import annotations


class UnverifiedGroupIdentity(ValueError):
    """The official response cannot prove the requested season/group binding."""


class VerifiedGroupFetcher:
    """Fetch standings only for an exact, freshly checked official group.

    The caller provides the representative team selected explicitly when
    following a group. No representative team is chosen by a search result.
    Current FBM phase responses do not expose a verified season ID, therefore
    this bridge deliberately refuses network standings requests today.
    """

    def __init__(self, client, representative_teams):
        self.client = client
        self.representative_teams = representative_teams

    @staticmethod
    def _validated(identity, season_id, group_id, team_id):
        if not isinstance(identity, dict) or identity.get("source") != "FBM":
            raise UnverifiedGroupIdentity("La respuesta no acredita procedencia FBM")
        if identity.get("season_verified") is not True:
            raise UnverifiedGroupIdentity("Temporada oficial pendiente de verificar")
        if not all(type(identity.get(k)) is str and identity[k] == expected for k, expected in (
            ("season_id", season_id), ("group_id", group_id), ("team_id", team_id)
        )):
            raise UnverifiedGroupIdentity("La relación temporada/grupo/equipo no coincide")

    async def __call__(self, season_id: str, group_id: str) -> dict:
        team_id = self.representative_teams.get((season_id, group_id))
        if type(team_id) is not str or not team_id.strip():
            raise UnverifiedGroupIdentity("No hay equipo representante verificado")
        identity = await self.client.async_team_group_identity(team_id)
        self._validated(identity, season_id, group_id, team_id)
        # Revalidate immediately before storage: if FBM reassigns an active
        # team to another group, never write it under the old group's key.
        standings = await self.client.async_team_standings(team_id)
        if not isinstance(standings, dict) or not isinstance(standings.get("clasificacion"), list):
            raise ValueError("Respuesta de clasificación inválida")
        return standings
