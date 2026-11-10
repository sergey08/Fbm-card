"""Read-only FBM diagnostics: strict allowlisted schema metadata, no values.

Never surface raw responses, auth fields, request bodies, IDs or exception strings.
"""
from __future__ import annotations
import re

SCHEDULE_KEYS = frozenset({
    "error", "partidos", "jornadas", "jornadaActual", "resultado", "listaJornadas",
})
ROSTER_KEYS = frozenset({
    "error", "misJugadores", "misjugadores", "jugadores", "total", "equipo",
})
ROSTER_ROW_KEYS = frozenset({
    "id", "nombre", "nombreEquipo", "temporada", "partidosJugados",
    "puntosTotales", "mediaPuntos", "puntosPorPartido", "minutosPorPartido",
})


def safe_error_category(exc: Exception) -> str:
    """Type-only diagnosis: never serialize exception messages or URLs."""
    code = getattr(exc, "code", None)
    if code in {"http_non_200", "network", "response_too_large", "invalid_json", "non_object_json"}:
        return code
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, (ConnectionError, OSError)):
        return "transport"
    if isinstance(exc, ValueError):
        return "invalid_payload_or_parameters"
    if isinstance(exc, RuntimeError):
        return "request_failed"
    return "unexpected"


def safe_payload_shape(payload: object, *, kind: str) -> dict:
    """Summary of known field presence/types, not arbitrary response keys."""
    keys = SCHEDULE_KEYS if kind == "schedule" else ROSTER_KEYS
    if type(payload) is not dict:
        return {"type": type(payload).__name__ if type(payload) in (list, str, int, bool, type(None)) else "other"}
    # Field names only; accept identifier-like ASCII keys, never arbitrary values.
    safe_keys = sorted(k for k in payload if isinstance(k, str)
                       and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", k)
                       and k.lower() not in {"key", "authorization", "token", "id_dispositivo", "uid", "password", "secret", "cookie", "session"})[:40]
    result = {
        "top_level_keys": safe_keys,
        "type": "object",
        "present": sorted(k for k in keys if k in payload),
        "error_type": type(payload["error"]).__name__ if "error" in payload else "missing",
        "error_empty_string": payload.get("error") == "",
    }
    for name in ("partidos", "jornadas", "listaJornadas", "misJugadores", "misjugadores", "jugadores"):
        if name not in keys:
            continue
        v = payload.get(name)
        if isinstance(v, list):
            result[name + "_count"] = len(v)
            if kind == "roster" and v and type(v[0]) is dict:
                row = v[0]
                result["first_row_present"] = sorted(k for k in ROSTER_ROW_KEYS if k in row)
                # Only key names and type labels; never the player/ID values.
                keys_only = sorted(k for k in row if type(k) is str
                                   and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", k)
                                   and k.lower() not in {"key", "authorization", "token", "id_dispositivo",
                                                         "uid", "password", "secret", "cookie", "session"})[:50]
                result["first_row_keys"] = keys_only
                result["first_row_types"] = {k: ("null" if row[k] is None else
                    "string" if type(row[k]) is str else
                    "number" if type(row[k]) in (int, float) else
                    "boolean" if type(row[k]) is bool else
                    "object" if type(row[k]) is dict else
                    "array" if type(row[k]) is list else "other")
                    for k in keys_only}
                if "Foto" in row:
                    result["player_photo_reference"] = _image_reference_kind(row["Foto"])
        elif name in payload:
            result[name + "_type"] = type(v).__name__ if type(v) in (str, dict, int, bool, type(None)) else "other"
    if kind == "schedule":
        matches = payload.get("partidos")
        if type(matches) is list and matches and type(matches[0]) is dict:
            first = matches[0]
            names = ("EscudoLocal", "EscudoVisitante", "escudoLocal",
                     "escudoVisitante", "IdEquipoLocal", "IdEquipoVisitante",
                     "idEquipoLocal", "idEquipoVisitante", "LogoLocal", "LogoVisitante")
            result["match_image_fields"] = [key for key in names if key in first]
            result["match_image_types"] = {
                key: _image_reference_kind(first[key]) for key in names if key in first
            }
    return result


def _image_reference_kind(value: object) -> str:
    """Classify an image reference without returning URLs, IDs or photographs."""
    if value is None:
        return "null"
    if type(value) is not str:
        return "other"
    if not value.strip():
        return "empty"
    if value.startswith("https://"):
        return "https_url"
    if value.startswith("http://"):
        return "http_url"
    if value.startswith("data:"):
        return "inline_data"
    return "opaque_reference"


def safe_player_detail_shape(payload: object) -> dict:
    """Known structural keys only; never values or arbitrary response keys."""
    if type(payload) is not dict:
        return {"type": "non_object"}
    fields = ("jugador", "Jugador", "equipo", "Equipo",
              "idComponenteClub", "IdComponenteClub",
              "idTemporadaActual", "IdTemporadaActual",
              "error", "resultado", "ruta", "opcion")
    player_fields = ("id", "Id", "nombre", "Nombre", "nombreEquipo",
                     "NombreEquipo", "temporada", "Temporada",
                     "categoria", "Categoria", "partidosJugados",
                     "PartidosJugados", "puntosTotales", "PuntosTotales",
                     "Foto", "foto", "IdJugadorFoto", "idJugadorFoto")
    result = {"type": "object",
              "present": [k for k in fields if k in payload],
              "error_empty": payload.get("error") == ""}
    for key in ("jugador", "Jugador"):
        if key in payload:
            item = payload[key]
            result["player_type"] = ("object" if type(item) is dict else
                                      "array" if type(item) is list else
                                      "null" if item is None else "other")
            if type(item) is dict:
                result["player_fields"] = [k for k in player_fields if k in item]
                result["photo_fields"] = {
                    k: _image_reference_kind(item[k]) for k in
                    ("Foto", "foto", "IdJugadorFoto", "idJugadorFoto") if k in item
                }
    for key in ("equipo", "Equipo"):
        if key in payload:
            result["team_type"] = "object" if type(payload[key]) is dict else "other"
            if type(payload[key]) is dict:
                result["team_fields"] = [k for k in ("id", "Id", "nombre", "Nombre") if k in payload[key]]
    return result


def safe_statistics_shape(payload: object, kind: str) -> dict:
    """Only shape/type metadata for known APK stats fields, never raw values."""
    if type(payload) is not dict:
        return {"type": "non_object"}
    fields = (
        ("error", "resultado", "ruta", "opcion", "puntosTotalesJugador",
         "puntosMediaJugador", "asistenciasTotalesJugador",
         "faltasCometidasTotalesJugador", "rebotesTotalesJugador",
         "mostrarDatosEstadisticosAmpliados")
        if kind == "global" else
        ("error", "resultado", "ruta", "opcion", "listaDatosPartido",
         "ListaDatosPartido", "listaDatosPartidos")
    )
    out = {"type": "object", "recognized": [k for k in fields if k in payload],
           "error_empty": payload.get("error") == ""}
    for key in ("listaDatosPartido", "ListaDatosPartido", "listaDatosPartidos"):
        if key in payload:
            rows = payload[key]
            out["row_type"] = "array" if type(rows) is list else "other"
            if type(rows) is list:
                out["count"] = len(rows)
                if rows and type(rows[0]) is dict:
                    # Field names/types only. Never return any cell values.
                    allowed = (
                        "idPartido", "IdPartido", "fechaPartido", "FechaPartido",
                        "nombreEquipoRival", "NombreEquipoRival", "local", "Local",
                        "puntos", "Puntos", "asistencia", "Asistencia",
                        "faltaCometida", "FaltaCometida", "faltaRecibida", "FaltaRecibida",
                        "rebotesTotal", "RebotesTotal", "rebotesDefensivos",
                        "RebotesDefensivos", "rebotesOfensivos", "RebotesOfensivos",
                        "recuperaciones", "Recuperaciones", "perdidas", "Perdidas",
                        "valoracion", "Valoracion",
                    )
                    first = rows[0]
                    out["first_row_fields"] = [k for k in allowed if k in first]
                    out["first_row_types"] = {
                        k: ("null" if first[k] is None else
                            "bool" if type(first[k]) is bool else
                            "number" if type(first[k]) in (int, float) else
                            "string" if type(first[k]) is str else "other")
                        for k in allowed if k in first
                    }
    return out
