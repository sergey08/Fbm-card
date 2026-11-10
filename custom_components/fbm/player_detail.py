"""Read-only FBM Afición player detail transport and conservative DTO mapper.

Source: APK 5.0.42 LH5/j;->e posts detalleJugador to /v2/jugador.ashx.
Never return profile photos, private response keys or unverified match data.
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request

from .device_protocol import open_request
from .player_protocol import player_detail_fields
from .image_references import image_data_uri


PLAYER_URL = "https://appaficionfbm.gesdeportiva.es/v2/jugador.ashx"


class PlayerDetailError(ValueError):
    """Invalid, unsupported or unavailable player detail."""


def _post_player_form(fields: dict[str, str], permitted: set[str]) -> dict:
    if not isinstance(fields, dict) or fields.get("accion") not in permitted:
        raise ValueError("Acción de jugador no autorizada")
    expected = {"accion", "id_dispositivo", "key", "id_jugador"}
    if fields.get("accion") != "detalleJugador":
        expected |= {"id_equipo", "id_componente_club", "id_temporada"}
    if set(fields) != expected:
        raise ValueError("Formulario de jugador no autorizado")
    if any(type(value) is not str or not value.strip() or len(value) > 1024
           for value in fields.values()):
        raise ValueError("Campos técnicos de jugador inválidos")
    request = urllib.request.Request(
        PLAYER_URL, data=urllib.parse.urlencode(fields).encode("utf-8"),
        method="POST", headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "FBMCard-DEV/0.1",
        },
    )
    try:
        with open_request(request, timeout=12) as response:
            if response.status != 200:
                raise PlayerDetailError("Respuesta HTTP inválida")
            body = response.read(131073)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise PlayerDetailError("No se pudo consultar la ficha") from None
    if len(body) > 131072:
        raise PlayerDetailError("Respuesta de ficha demasiado grande")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise PlayerDetailError("JSON de jugador no válido") from None
    if not isinstance(payload, dict):
        raise PlayerDetailError("Respuesta de ficha no válida")
    return payload


def post_player_detail_form(fields: dict[str, str]) -> dict:
    """APK detalleJugador: exact allowlist, no other actions."""
    return _post_player_form(fields, {"detalleJugador"})


def post_player_statistics_form(fields: dict[str, str]) -> dict:
    """APK statistics actions through the same official /v2/jugador.ashx."""
    return _post_player_form(
        fields, {"datosGlobalesJugadorEquipo", "datosMediasJugadorPartidos"}
    )


def normalize_player_detail(response: object, requested_player_id: str) -> dict:
    """Normalize either verified JSON casing without mixing the two variants."""
    if type(response) is not dict or response.get("error") != "":
        raise PlayerDetailError("Ficha de jugador no validada")
    raw = response.get("jugador")
    if type(raw) is not dict:
        raise PlayerDetailError("Falta el jugador")
    variants = (
        {"id": "id", "nombre": "nombre", "nombreEquipo": "equipo",
         "temporada": "temporada", "categoria": "categoria",
         "partidosJugados": "partidos_jugados", "puntosTotales": "puntos_totales",
         "mediaPuntos": "media_puntos", "puntosPorPartido": "puntos_por_partido",
         "minutosPorPartido": "minutos_por_partido"},
        {"Id": "id", "Nombre": "nombre", "NombreEquipo": "equipo",
         "Temporada": "temporada", "Categoria": "categoria",
         "PartidosJugados": "partidos_jugados", "PuntosTotales": "puntos_totales",
         "MediaPuntos": "media_puntos", "PuntosPorPartido": "puntos_por_partido",
         "MinutosPorPartido": "minutos_por_partido"},
    )
    matching = [mapping for mapping in variants
                if type(raw.get(next(k for k,v in mapping.items() if v == "id"))) is str
                and type(raw.get(next(k for k,v in mapping.items() if v == "nombre"))) is str]
    if len(matching) != 1:
        raise PlayerDetailError("Identidad deportiva no validada")
    mapping = matching[0]
    other = variants[1] if mapping is variants[0] else variants[0]
    if any(field in raw for field in other):
        raise PlayerDetailError("Formato de ficha mezclado")
    ident = next(k for k,v in mapping.items() if v == "id")
    name_key = next(k for k,v in mapping.items() if v == "nombre")
    player_id, name = raw[ident], raw[name_key]
    if player_id != requested_player_id or not name.strip() or len(name) > 256:
        raise PlayerDetailError("Identidad deportiva no coincide")
    result = {"id": player_id, "nombre": name}
    for source, target in mapping.items():
        if target in ("id", "nombre"):
            continue
        value = raw.get(source)
        if target in ("equipo", "temporada", "categoria"):
            if value is not None and (type(value) is not str or len(value) > 256):
                raise PlayerDetailError("Campo deportivo inválido")
        elif value is not None:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise PlayerDetailError("Estadística deportiva inválida")
            if mapping is variants[1] and target == "puntos_totales" and type(value) is int and value == -1:
                value = None
            elif value < 0 or value >= 1000000:
                raise PlayerDetailError("Estadística deportiva inválida")
            elif target == "partidos_jugados" and type(value) is not int:
                raise PlayerDetailError("Partidos jugados no es entero")
        result[target] = value
    photo = image_data_uri(raw.get("Foto" if mapping is variants[1] else "foto"))
    if photo:
        result["foto"] = photo
    return {"jugador": result, "fuente": "FBM"}
