"""Normalize team roster using APK 5.0.42 JugadoresEquipoResponseDto.

The APK uses "misJugadores" and JugadorEquipoDto uses lower camelCase.
No network calls or inferred statistics. Only explicitly present public
basketball fields are passed through. Deployment remains disabled until
the official response and permitted fields are verified in live testing.
"""
from __future__ import annotations


class PlayerRosterError(ValueError):
    """Roster payload is not a recognized official structure."""


def normalize_team_roster(response: object) -> dict:
    if not isinstance(response, dict) or response.get("error") != "":
        raise PlayerRosterError("Respuesta de plantilla no validada")
    roster = response.get("misJugadores")
    if not isinstance(roster, list):
        raise PlayerRosterError("Falta misJugadores")

    players = []
    seen = set()
    text_fields = {
        "nombreEquipo": "equipo",
        "temporada": "temporada",
    }
    int_fields = {
        "partidosJugados": "partidos_jugados",
        "puntosTotales": "puntos_totales",
        "mediaPuntos": "media_puntos",
    }
    float_fields = {
        "puntosPorPartido": "puntos_por_partido",
        "minutosPorPartido": "minutos_por_partido",
    }
    for raw in roster:
        if not isinstance(raw, dict):
            raise PlayerRosterError("Jugador inválido")
        ident, name = raw.get("id"), raw.get("nombre")
        if (type(ident) is not str or not ident.strip() or len(ident) > 512
                or type(name) is not str or not name.strip() or len(name) > 256):
            raise PlayerRosterError("Jugador sin identificador y nombre oficiales")
        if ident in seen:
            raise PlayerRosterError("Identificador de jugador duplicado")
        seen.add(ident)
        player = {"id": ident, "nombre": name}
        for source, target in text_fields.items():
            value = raw.get(source)
            if value is not None and (type(value) is not str or len(value) > 256):
                raise PlayerRosterError("Campo de jugador inválido")
            player[target] = value
        for source, target in int_fields.items():
            value = raw.get(source)
            if value is not None and (type(value) is not int or value < 0):
                raise PlayerRosterError("Estadística de jugador inválida")
            player[target] = value
        for source, target in float_fields.items():
            value = raw.get(source)
            if value is not None and (type(value) not in (float, int)
                                      or not 0 <= value < 1000000):
                raise PlayerRosterError("Promedio de jugador inválido")
            player[target] = value
        players.append(player)
    return {"jugadores": players, "total": len(players)}
