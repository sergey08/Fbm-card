"""Read-only FBM Afición player detail transport and conservative DTO mapper.

Source: APK 5.0.42 LH5/j;->e posts detalleJugador to /v2/jugador.ashx.
Never return profile photos, private response keys or unverified match data.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .device_protocol import open_request
from .player_protocol import player_detail_fields

PLAYER_URL = "https://appaficionfbm.gesdeportiva.es/v2/jugador.ashx"


class PlayerDetailError(ValueError):
    """Invalid, unsupported or unavailable player detail."""


def post_player_detail_form(fields: dict[str, str]) -> dict:
    if not isinstance(fields, dict) or set(fields) != {
        "accion", "id_dispositivo", "key", "id_jugador"
    } or fields.get("accion") != "detalleJugador":
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


def normalize_player_detail(response: object, requested_player_id: str) -> dict:
    if not isinstance(response, dict) or response.get("error") != "":
        raise PlayerDetailError("Ficha de jugador no validada")
    raw = response.get("jugador")
    if not isinstance(raw, dict):
        raise PlayerDetailError("Falta el jugador")
    player_id, name = raw.get("id"), raw.get("nombre")
    if (type(player_id) is not str or player_id != requested_player_id
            or type(name) is not str or not name.strip() or len(name) > 256):
        raise PlayerDetailError("Identidad deportiva del jugador no coincide")
    result = {"id": player_id, "nombre": name}
    for source, target in (
        ("nombreEquipo", "equipo"),
        ("temporada", "temporada"),
        ("categoria", "categoria"),
    ):
        value = raw.get(source)
        if value is not None and (type(value) is not str or len(value) > 256):
            raise PlayerDetailError("Campo deportivo inválido")
        result[target] = value
    for source, target in (
        ("partidosJugados", "partidos_jugados"),
        ("puntosTotales", "puntos_totales"),
        ("mediaPuntos", "media_puntos"),
        ("puntosPorPartido", "puntos_por_partido"),
        ("minutosPorPartido", "minutos_por_partido"),
    ):
        value = raw.get(source)
        if value is not None and (type(value) not in (int, float)
                                  or not 0 <= value < 1000000):
            raise PlayerDetailError("Estadística deportiva inválida")
        result[target] = value
    return {"jugador": result, "fuente": "FBM"}
