"""Normalize schedule from FBM Afición 5.0.42 DTO fields, conservatively.

The APK's EquipoPartidoDto/ResultadosDto expose camelCase fields. Keep the
older experimental PascalCase mapping for compatibility, without mixing them.
"""
from __future__ import annotations


class TeamScheduleError(ValueError):
    """Official schedule payload has an unrecognized or unsafe shape."""


def _normalize_matches(matches: list) -> list:
    """Common official match renderer for team and competition schedules."""

    required_variants = (
        {"idPartido": "id", "nombreEquipoLocal": "local", "nombreEquipoVisitante": "visitante"},
        {"IdPartido": "id", "NombreEquipoLocal": "local", "NombreEquipoVisitante": "visitante"},
    )
    optional_variants = (
        {"fecha": "fecha", "hora": "hora", "fechaHoraUTC": "fecha_hora_utc",
         "campoJuego": "campo", "direccionCampo": "direccion", "estado": "estado_oficial"},
        {"Fecha": "fecha", "Hora": "hora", "FechaHoraUTC": "fecha_hora_utc",
         "CampoJuego": "campo", "DireccionCampo": "direccion", "Estado": "estado_oficial"},
    )
    normalized = []
    for item in matches:
        if not isinstance(item, dict):
            raise TeamScheduleError("Partido inválido")
        valid_variants = [
            idx for idx, required in enumerate(required_variants)
            if all(type(item.get(k)) is str and item[k].strip() for k in required)
        ]
        if len(valid_variants) != 1:
            raise TeamScheduleError("Partido sin identificador único o equipos")
        idx = valid_variants[0]
        required, optional = required_variants[idx], optional_variants[idx]
        record = {out: item[name] for name, out in required.items()}
        for name, out in optional.items():
            value = item.get(name)
            if value is not None and type(value) is not str:
                raise TeamScheduleError("Campo de partido inesperado")
            record[out] = value
        number = item.get("numeroJornada" if idx == 0 else "NumeroJornada")
        if number is not None and type(number) is not int:
            raise TeamScheduleError("Número de jornada no válido")
        record["jornada"] = number
        state = record["estado_oficial"]
        record["estado"] = {"Terminado": "finished", "No comenzado": "scheduled"}.get(state, "unknown")
        results = item.get("resultados" if idx == 0 else "Resultados")
        record["marcador"] = None
        if record["estado"] == "finished" and isinstance(results, dict):
            local, away = (results.get("resultadoLocal"), results.get("resultadoVisitante")) if idx == 0 else (
                results.get("ResultadoLocal"), results.get("ResultadoVisitante"))
            if (type(local) is str and type(away) is str and
                    local.isascii() and away.isascii() and
                    local.isdecimal() and away.isdecimal()):
                record["marcador"] = {"local": int(local), "visitante": int(away)}
        normalized.append(record)
    return normalized


def normalize_team_schedule(response: object) -> dict:
    """EquipoPartidoResponseDto includes jornadaActual and partidos."""
    if not isinstance(response, dict) or response.get("error") != "":
        raise TeamScheduleError("Respuesta de horarios ambigua o con error")
    matches, current_round = response.get("partidos"), response.get("jornadaActual")
    if not isinstance(matches, list) or type(current_round) is not int:
        raise TeamScheduleError("Faltan partidos o jornada actual")
    return {"jornada_actual": current_round, "partidos": _normalize_matches(matches)}


def normalize_category_schedule(response: object) -> dict:
    """PartidosCategoriaResponseDto contains partidos but no jornadaActual.

    Do not fabricate a current matchday, and do not invent fixtures from
    unrelated category-level data.
    """
    if not isinstance(response, dict) or response.get("error") != "":
        raise TeamScheduleError("Respuesta de categoría ambigua o con error")
    matches = response.get("partidos")
    if not isinstance(matches, list):
        raise TeamScheduleError("Falta la lista de partidos de categoría")
    return {"jornada_actual": None, "partidos": _normalize_matches(matches)}

