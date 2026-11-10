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
        elif name in payload:
            result[name + "_type"] = type(v).__name__ if type(v) in (str, dict, int, bool, type(None)) else "other"
    return result


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
                     "PartidosJugados", "puntosTotales", "PuntosTotales")
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
    for key in ("equipo", "Equipo"):
        if key in payload:
            result["team_type"] = "object" if type(payload[key]) is dict else "other"
    return result
