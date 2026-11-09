"""Normaliza clasificaciones de grupo sin recalcular puntuaciones."""
from __future__ import annotations


class TeamStandingsError(ValueError):
    """La respuesta de clasificacion no tiene el formato esperado."""


def normalize_standings(response: object) -> dict:
    """Conserva el orden y los valores observados, sin inferir posiciones."""
    if not isinstance(response, dict) or response.get("error") != "":
        raise TeamStandingsError("Respuesta de clasificacion ambigua o con error")
    rows = response.get("clasificacion")
    if not isinstance(rows, list):
        raise TeamStandingsError("Falta lista de clasificacion")
    numbers = {"Posicion": "posicion", "PartidosJugados": "jugados",
               "PartidosGanados": "ganados", "PartidosPerdidos": "perdidos", "Puntos": "puntos"}
    normalized = []
    for item in rows:
        if not isinstance(item, dict):
            raise TeamStandingsError("Fila de clasificacion invalida")
        team_id, name = item.get("IdEquipo"), item.get("NombreEquipo")
        if not isinstance(team_id, str) or not team_id.strip() or not isinstance(name, str) or not name.strip():
            raise TeamStandingsError("Fila sin equipo")
        if any(type(item.get(key)) is not int for key in numbers):
            raise TeamStandingsError("Valores numericos de clasificacion invalidos")
        row = {"id": team_id, "equipo": name}
        row.update({target: item[source] for source, target in numbers.items()})
        # El campo es opcional; su formato real aún requiere verificación.
        crest = item.get("Escudo")
        if isinstance(crest, str) and crest.strip() and len(crest) <= 1024:
            row["escudo"] = crest.strip()
        normalized.append(row)
    return {"clasificacion": normalized}


