"""Read shot locations from the Afición FBM match endpoint."""
from __future__ import annotations

import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request

from .device_protocol import open_request

SHOT_MAP_URL = "https://appaficionfbm.gesdeportiva.es/v2/envivo/mapa-de-tiro.ashx"
MAX_RESPONSE_BYTES = 1024 * 1024


class ShotMapError(ValueError):
    """FBM did not return a usable shot map."""


def post_shot_map(device_id: str, key: str, match_id: str) -> dict:
    fields = {"id_dispositivo": device_id, "key": key, "id_partido": match_id}
    if any(not isinstance(value, str) or not value.strip() for value in fields.values()):
        raise ShotMapError("Faltan datos de sesión o partido.")
    request = Request(
        SHOT_MAP_URL, data=urlencode(fields).encode(), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "FBMCard-DEV/0.1"},
    )
    try:
        with open_request(request, timeout=12) as response:
            if response.status != 200:
                raise ShotMapError("Respuesta HTTP del mapa de tiro no válida.")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (URLError, OSError):
        raise ShotMapError("No se pudo consultar el mapa de tiro en FBM.") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ShotMapError("Respuesta del mapa de tiro demasiado grande.")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise ShotMapError("JSON del mapa de tiro no válido.") from None
    return normalize_shot_map(payload)


def normalize_shot_map(payload: object) -> dict:
    if not isinstance(payload, dict) or payload.get("error") != "" or payload.get("resultado") == "error":
        raise ShotMapError("FBM no ha facilitado el mapa de tiro.")
    shot_map = payload.get("mapadetiro")
    if not isinstance(shot_map, dict) or not isinstance(shot_map.get("tiros"), list):
        raise ShotMapError("Estructura del mapa de tiro no válida.")
    shots = []
    for row in shot_map["tiros"]:
        if not isinstance(row, dict):
            continue
        raw_x, raw_y = row.get("posicion_x"), row.get("posicion_y")
        if any(type(value) not in (str, int, float) for value in (raw_x, raw_y)):
            continue
        try:
            x, y = float(raw_x), float(raw_y)
        except (ValueError, OverflowError):
            continue
        period, local = row.get("numero_periodo"), row.get("local")
        made, missed = row.get("metido"), row.get("fallado")
        if (not (0 <= x <= 100 and 0 <= y <= 100) or
                type(period) is not int or period < 1 or type(local) is not bool or
                type(made) is not int or type(missed) is not int or
                (made, missed) not in ((1, 0), (0, 1))):
            continue
        shot = {"x": x, "y": y, "periodo": period, "local": local, "metido": bool(made)}
        for field in ("componente_id", "dorsal", "zona"):
            if isinstance(row.get(field), str) and row[field]:
                shot[field] = row[field]
        shots.append(shot)
    return {"tiros": shots, "tiros_descartados": len(shot_map["tiros"]) - len(shots)}
