"""Afición FBM 5.0.42 per-player match-stat DTO normalization.

Field names are taken from EstadisticasJugadorEquipoPartidoDto in the APK.
This handles one DTO only; the enclosing response path and availability for
minor age categories must be verified before enabling any network/UI feature.
"""
from __future__ import annotations


class MatchPlayerStatsError(ValueError):
    """Invalid or unsupported player-stat DTO."""


def normalize_match_player_stats(item: object) -> dict:
    if not isinstance(item, dict):
        raise MatchPlayerStatsError("Estadística no es un objeto")
    name = item.get("nombre")
    if type(name) is not str or not name.strip() or len(name) > 256:
        raise MatchPlayerStatsError("Jugador sin nombre")
    result = {"nombre": name}
    for source, target in (
        ("componente_id", "componente_id"),
        ("dorsal", "dorsal"),
        ("equipo", "equipo"),
        ("tiempo_jugado", "tiempo_jugado"),
    ):
        value = item.get(source)
        if value is not None and (type(value) is not str or len(value) > 256):
            raise MatchPlayerStatsError("Campo de jugador inválido")
        result[target] = value
    for source, target in (
        ("puntos", "puntos"),
        ("faltascometidas", "faltas_cometidas"),
        ("faltasrecibidas", "faltas_recibidas"),
        ("rebotes", "rebotes"),
        ("rebotedefensivo", "rebotes_defensivos"),
        ("reboteofensivo", "rebotes_ofensivos"),
        ("asistencias", "asistencias"),
        ("recuperaciones", "recuperaciones"),
        ("perdidas", "perdidas"),
        ("valoracion", "valoracion"),
    ):
        value = item.get(source)
        if value is not None and (type(value) is not int or (value < 0 and target != "valoracion")):
            raise MatchPlayerStatsError("Estadística numérica inválida")
        result[target] = value
    return result
