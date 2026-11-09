"""Fail-closed binding for player statistics, from APK 5.0.42 detail DTO.

JugadorDetalleResponseDto has jugador, equipo, idComponenteClub,
idTemporadaActual. Never infer any identifier from display names or dates.
Use only a raw official detail response held transiently inside the adapter.
"""
from __future__ import annotations


class PlayerContextUnverified(ValueError):
    """The official detail did not prove the exact player/team/season binding."""


def verified_player_stats_context(response: object, player_id: str, team_id: str) -> dict:
    def checked(value, expected=None):
        if type(value) is not str or not value.strip() or len(value) > 512:
            raise PlayerContextUnverified("Identificador oficial no disponible")
        if expected is not None and value != expected:
            raise PlayerContextUnverified("Identificador oficial no coincide")
        return value

    checked(player_id)
    checked(team_id)
    if not isinstance(response, dict) or response.get("error") != "":
        raise PlayerContextUnverified("Respuesta de ficha no validada")
    player, team = response.get("jugador"), response.get("equipo")
    if not isinstance(player, dict) or not isinstance(team, dict):
        raise PlayerContextUnverified("Falta asociación explícita jugador-equipo")
    checked(player.get("id"), player_id)
    checked(team.get("id"), team_id)
    component = checked(response.get("idComponenteClub"))
    season = checked(response.get("idTemporadaActual"))
    # Do not output any raw response, session metadata or display attributes.
    return {"id_jugador": player_id, "id_equipo": team_id,
            "id_componente_club": component, "id_temporada": season}
