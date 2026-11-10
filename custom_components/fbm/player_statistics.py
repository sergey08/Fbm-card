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
    variants = (
        ({"id": "idPartido", "fecha": "fechaPartido", "rival": "nombreEquipoRival",
          "local": "local"}, _MATCH_NUMBERS),
        ({"id": "IdPartido", "fecha": "FechaPartido", "rival": "NombreEquipoRival",
          "local": "Local"}, {source[0].upper() + source[1:]: output for source, output in _MATCH_NUMBERS.items()}),
    )
    for row in rows:
        if type(row) is not dict:
            raise PlayerStatisticsError("Partido inválido")
        found = [v for v in variants if type(row.get(v[0]["id"])) is str]
        if len(found) != 1:
            raise PlayerStatisticsError("Identificador de partido ausente o ambiguo")
        fields, numbers = found[0]
        other_fields, other_numbers = variants[1] if found[0] is variants[0] else variants[0]
        if any(k in row for k in (*other_fields.values(), *other_numbers)):
            raise PlayerStatisticsError("Mezcla de formatos de estadísticas de partido")
        match_id = row[fields["id"]]
        if not match_id.strip() or len(match_id) > 512 or match_id in seen:
            raise PlayerStatisticsError("ID de partido ausente o repetido")
        seen.add(match_id)
        record = {"id_partido": match_id}
        for dest in ("fecha", "rival"):
            value = row.get(fields[dest])
            if value is not None and (type(value) is not str or len(value) > 256):
                raise PlayerStatisticsError("Dato de partido inválido")
            record[dest] = value
        local = row.get(fields["local"])
        if local is not None and type(local) is not bool:
            raise PlayerStatisticsError("Localía inválida")
        record["local"] = local
        for source, output in numbers.items():
            record[output] = _number(row.get(source), signed=output == "valoracion")
        matches.append(record)
    return {"partidos": matches, "total": len(matches)}


def _text_stat_category(value: str) -> str:
    """Return only a fixed category label, never server-supplied text."""
    stripped = value.strip()
    if not stripped:
        return "whitespace"
    if stripped in ("-", "--", "—", "–"):
        return "dash_placeholder"
    if stripped.upper() in ("N/A", "N.D.", "ND", "S/D", "N/D"):
        return "unavailable_label"
    if stripped.replace(",", "", 1).replace(".", "", 1).lstrip("-").isdigit():
        return "decimal_separator"
    if any(ch.isalpha() for ch in stripped):
        return "alphabetic_text"
    return "other_symbols"


def diagnose_match_rows(response: object) -> dict:
    """Count official field types and validation failures without exposing values."""
    if type(response) is not dict or response.get("error") != "":
        return {"status": "invalid_response"}
    rows = response.get("listaDatosPartido")
    if type(rows) is not list:
        return {"status": "invalid_list"}
    labels = {
        "Partido inválido": "invalid_row",
        "Identificador de partido ausente o ambiguo": "invalid_id_type",
        "ID de partido ausente o repetido": "invalid_or_duplicate_id",
        "Mezcla de formatos de estadísticas de partido": "mixed_casing",
        "Dato de partido inválido": "invalid_text",
        "Localía inválida": "invalid_home_flag",
        "Estadística booleana inválida": "boolean_statistic",
        "Estadística no numérica": "non_numeric_statistic",
        "Estadística inválida": "invalid_number",
        "Estadística negativa": "negative_statistic",
    }
    errors, types, seen_ids = {}, {}, set()
    number_keys = tuple(_MATCH_NUMBERS) + tuple(k[0].upper() + k[1:] for k in _MATCH_NUMBERS)
    for row in rows:
        if type(row) is dict:
            for field in number_keys:
                if field not in row:
                    continue
                value = row[field]
                kind = ("null" if value is None else
                        "bool" if type(value) is bool else
                        "int" if type(value) is int else
                        "float" if type(value) is float else
                        "empty" if type(value) is str and value == "" else
                        "numeric_text" if type(value) is str and value.isascii()
                        and value.lstrip("-").isdecimal() else
                        "other_text" if type(value) is str else "other")
                counts = types.setdefault(field, {})
                counts[kind] = counts.get(kind, 0) + 1
                if kind == "other_text":
                    label = _text_stat_category(value)
                    patterns = counts.setdefault("text_patterns", {})
                    patterns[label] = patterns.get(label, 0) + 1
                if type(value) in (int, float) and value < 0 or (
                    type(value) is str and value == "-1"):
                    counts["negative_count"] = counts.get("negative_count", 0) + 1
        try:
            normalize_player_match_list({"error": "", "listaDatosPartido": [row]})
        except PlayerStatisticsError as exc:
            label = labels.get(str(exc), "other_validation")
            errors[label] = errors.get(label, 0) + 1
        if type(row) is dict:
            match_id = row.get("IdPartido", row.get("idPartido"))
            if type(match_id) is str:
                if match_id in seen_ids:
                    errors["duplicate_across_rows"] = errors.get("duplicate_across_rows", 0) + 1
                seen_ids.add(match_id)
    return {"status": "diagnosed", "total": len(rows),
            "errors": errors, "statistic_types": types}
