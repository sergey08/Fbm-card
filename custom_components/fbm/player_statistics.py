"""Conservative normalizers for APK 5.0.42 player statistics DTOs.

LH5/j;->c returns JugadorDatosGlobalesResponseDto; ->d returns
DatosMediasJugadorPartidosResponseDto containing listaDatosPartido.
Do not infer missing statistics or publish additional player metadata.
"""
from __future__ import annotations
import math


class PlayerStatisticsError(ValueError):
    """Statistics response is unavailable or structurally unverified."""


_GLOBAL = {
    "puntosTotalesJugador": "puntos_totales",
    "puntosMediaJugador": "media_puntos",
    "asistenciasTotalesJugador": "asistencias",
    "faltasCometidasTotalesJugador": "faltas_cometidas",
    "faltasRecibidasTotalesJugador": "faltas_recibidas",
    "rebotesTotalesJugador": "rebotes",
    "rebotesDefensivosTotalesJugador": "rebotes_defensivos",
    "rebotesOfensivosTotalesJugador": "rebotes_ofensivos",
    "recuperacionesTotalesJugador": "recuperaciones",
    "perdidasTotalesJugador": "perdidas",
    "valoracionTotalJugador": "valoracion",
}
_MATCH_NUMBERS = {
    "puntos": "puntos", "asistencia": "asistencias",
    "faltaCometida": "faltas_cometidas", "faltaRecibida": "faltas_recibidas",
    "rebotesTotal": "rebotes", "rebotesDefensivos": "rebotes_defensivos",
    "rebotesOfensivos": "rebotes_ofensivos", "recuperaciones": "recuperaciones",
    "perdidas": "perdidas", "valoracion": "valoracion",
}


def _validated(response: object) -> dict:
    if not isinstance(response, dict) or response.get("error") != "":
        raise PlayerStatisticsError("Respuesta de estadísticas no validada")
    return response


def _number(value, *, signed=False):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise PlayerStatisticsError("Estadística booleana inválida")
    if isinstance(value, str):
        if not value.isascii() or not value.lstrip("-").isdecimal():
            raise PlayerStatisticsError("Estadística no numérica")
        value = int(value)
    if type(value) not in (int, float) or not math.isfinite(value):
        raise PlayerStatisticsError("Estadística inválida")
    if not signed and value < 0:
        raise PlayerStatisticsError("Estadística negativa")
    return value


def normalize_global_player_stats(response: object) -> dict:
    data = _validated(response)
    result = {}
    for source, key in _GLOBAL.items():
        result[key] = _number(data.get(source), signed=key == "valoracion")
    extended = data.get("mostrarDatosEstadisticosAmpliados")
    if extended is not None and type(extended) is not bool:
        raise PlayerStatisticsError("Cobertura estadística inválida")
    return {"estadisticas": result, "ampliadas_disponibles": extended}


def normalize_player_match_list(response: object) -> dict:
    data = _validated(response)
    rows = data.get("listaDatosPartido")
    if not isinstance(rows, list) or len(rows) > 1000:
        raise PlayerStatisticsError("Lista de partidos no válida")
    matches = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise PlayerStatisticsError("Partido inválido")
        match_id = row.get("idPartido")
        if type(match_id) is not str or not match_id.strip() or len(match_id) > 512 or match_id in seen:
            raise PlayerStatisticsError("ID de partido ausente o repetido")
        seen.add(match_id)
        record = {"id_partido": match_id}
        for field, output in (("fechaPartido", "fecha"), ("nombreEquipoRival", "rival")):
            value = row.get(field)
            if value is not None and (type(value) is not str or len(value) > 256):
                raise PlayerStatisticsError("Dato de partido inválido")
            record[output] = value
        local = row.get("local")
        if local is not None and type(local) is not bool:
            raise PlayerStatisticsError("Localía inválida")
        record["local"] = local
        for source, output in _MATCH_NUMBERS.items():
            record[output] = _number(row.get(source), signed=output == "valoracion")
        matches.append(record)
    return {"partidos": matches, "total": len(matches)}
