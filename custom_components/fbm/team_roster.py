"""Normalize official FBM team rosters without inferring missing statistics.

Live Afición FBM 5.0.42 returns 'misjugadores' with PascalCase rows.
Older experimentally observed DTOs used camelCase. Accept either complete
variant, never combine different spellings within a single player.
Only selected sporting fields are emitted; photos and club metadata stay out.
"""
from __future__ import annotations
import math


class PlayerRosterError(ValueError):
    """Roster payload is not a recognized official structure."""


_VARIANTS = (
    {"id": "id", "nombre": "nombre", "nombreEquipo": "equipo",
     "temporada": "temporada", "partidosJugados": "partidos_jugados",
     "puntosTotales": "puntos_totales", "mediaPuntos": "media_puntos",
     "puntosPorPartido": "puntos_por_partido", "minutosPorPartido": "minutos_por_partido"},
    {"Id": "id", "Nombre": "nombre", "NombreEquipo": "equipo",
     "Temporada": "temporada", "PartidosJugados": "partidos_jugados",
     "PuntosTotales": "puntos_totales", "MediaPuntos": "media_puntos",
     "PuntosPorPartido": "puntos_por_partido", "MinutosPorPartido": "minutos_por_partido"},
)


def normalize_team_roster(response: object) -> dict:
    if type(response) is not dict or response.get("error") != "":
        raise PlayerRosterError("Respuesta de plantilla no validada")
    keys = [key for key in ("misJugadores", "misjugadores") if key in response]
    if len(keys) != 1 or type(response[keys[0]]) is not list:
        raise PlayerRosterError("Lista de jugadores ausente, ambigua o no válida")

    players, seen = [], set()
    for raw in response[keys[0]]:
        if type(raw) is not dict:
            raise PlayerRosterError("Jugador inválido")
        variants = [mapping for mapping in _VARIANTS
                    if type(raw.get(next(k for k,v in mapping.items() if v == "id"))) is str
                    and type(raw.get(next(k for k,v in mapping.items() if v == "nombre"))) is str]
        if len(variants) != 1:
            raise PlayerRosterError("Jugador sin identificador y nombre de un formato conocido")
        mapping = variants[0]
        ident_key = next(k for k,v in mapping.items() if v == "id")
        name_key = next(k for k,v in mapping.items() if v == "nombre")
        ident, name = raw[ident_key], raw[name_key]
        if not ident.strip() or len(ident) > 512 or not name.strip() or len(name) > 256 or ident in seen:
            raise PlayerRosterError("Jugador incompleto o repetido")
        # Reject mixed naming of recognized sports fields, not unknown DTO extras.
        other = _VARIANTS[1] if mapping is _VARIANTS[0] else _VARIANTS[0]
        if any(k in raw for k in other):
            raise PlayerRosterError("Campos de dos variantes mezclados")
        seen.add(ident)
        item = {"id": ident, "nombre": name}
        for source, target in mapping.items():
            if target in ("id", "nombre"):
                continue
            value = raw.get(source)
            if target in ("equipo", "temporada"):
                if value is not None and (type(value) is not str or len(value) > 256):
                    raise PlayerRosterError("Campo de texto no válido")
            elif target in ("partidos_jugados", "puntos_totales"):
                if value == -1 and type(value) is int:
                    # FBM may mark unavailable counts as -1; never display it as a stat.
                    value = None
                elif value is not None and (type(value) is not int or value < 0):
                    raise PlayerRosterError("Estadística entera no válida")
            else:
                if value is not None and (type(value) not in (int, float)
                                          or not math.isfinite(value) or value < 0 or value >= 1000000):
                    raise PlayerRosterError("Promedio no válido")
            item[target] = value
        players.append(item)
    return {"jugadores": players, "total": len(players)}


def diagnose_roster_rows(response: object) -> dict:
    """Aggregate fixed error categories and type distributions, never values.

    Reuses the production parser for each row, so diagnostic observations
    cannot silently bypass its strict accepted shapes. No names/IDs returned.
    """
    if type(response) is not dict or response.get("error") != "":
        return {"status": "invalid_response"}
    keys = [k for k in ("misJugadores", "misjugadores") if k in response]
    if len(keys) != 1 or type(response[keys[0]]) is not list:
        return {"status": "invalid_roster"}
    rows = response[keys[0]]
    problems = {}
    number_types = {}
    labels = {
        "Jugador inválido": "row_not_object",
        "Jugador sin identificador y nombre de un formato conocido": "id_or_name_format",
        "Jugador incompleto o repetido": "missing_or_duplicated_id",
        "Campos de dos variantes mezclados": "mixed_variants",
        "Campo de texto no válido": "invalid_text",
        "Estadística entera no válida": "invalid_integer",
        "Promedio no válido": "invalid_average",
    }
    for raw in rows:
        if type(raw) is dict:
            for field in ("PartidosJugados", "PuntosTotales", "MediaPuntos",
                          "PuntosPorPartido", "MinutosPorPartido",
                          "partidosJugados", "puntosTotales", "mediaPuntos",
                          "puntosPorPartido", "minutosPorPartido"):
                if field in raw:
                    value = raw[field]
                    kind = ("null" if value is None else
                            "bool" if type(value) is bool else
                            "int" if type(value) is int else
                            "float" if type(value) is float else
                            "str" if type(value) is str else "other")
                    dist = number_types.setdefault(field, {})
                    dist[kind] = dist.get(kind, 0) + 1
                    if type(value) in (int, float) and value < 0:
                        sign_counts = dist.setdefault("negative_count", 0)
                        dist["negative_count"] = sign_counts + 1
                        if value == -1:
                            dist["minus_one_count"] = dist.get("minus_one_count", 0) + 1
        try:
            normalize_team_roster({"error": "", keys[0]: [raw]})
        except PlayerRosterError as exc:
            code = labels.get(str(exc), "other_validation")
            problems[code] = problems.get(code, 0) + 1
    return {"status": "diagnosed", "total": len(rows),
            "validation_errors": problems, "numeric_types": number_types}
