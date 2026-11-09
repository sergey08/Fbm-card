"""Safe metadata-only summary of FBM schedule response structures.

No network requests, personal fields, authentication data or raw error text.
"""
from __future__ import annotations

_RESPONSE_KEYS = ("error", "partidos", "jornadas", "jornadaActual", "resultado", "listaJornadas")
_ENTRY_KEYS = (
    # Exact field names identified in APK 5.0.42 EquipoPartidoDto.
    "idPartido", "nombreEquipoLocal", "nombreEquipoVisitante", "fecha", "hora",
    "numeroJornada", "resultados", "estado", "fechaHoraUTC", "campoJuego",
    # Legacy experimental response shape.
    "IdPartido", "NombreEquipoLocal", "NombreEquipoVisitante", "Fecha",
    "Hora", "NumeroJornada", "Resultados", "Estado",
    # Jornada/competition mode.
    "idJornada", "partidos",
)


def summarize_schedule_shape(response: object) -> dict:
    if not isinstance(response, dict):
        return {"shape": "not_object", "recognized": [], "entry_fields": [], "counts": {}}
    recognized = [k for k in _RESPONSE_KEYS if k in response]
    arrays = {k: response[k] for k in ("partidos", "jornadas", "listaJornadas")
              if type(response.get(k)) is list}
    counts = {k: len(v) for k, v in arrays.items()}
    entry_fields = []
    for array in arrays.values():
        if array and isinstance(array[0], dict):
            entry_fields = [k for k in _ENTRY_KEYS if k in array[0]]
            break
    return {"shape": "object", "recognized": recognized,
            "entry_fields": entry_fields, "counts": counts,
            "has_error": response.get("error") not in (None, "")}
