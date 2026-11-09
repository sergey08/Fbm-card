"""Operaciones experimentales de fases y horarios observadas en FBM."""
from __future__ import annotations

from datetime import date
import json
import urllib.error
import urllib.parse
import urllib.request

from .team_phases import classification_selection, schedule_selection
from .device_protocol import open_request

TEAM_URL = "https://appaficionfbm.gesdeportiva.es/v2/equipo.ashx"


def phases_fields(device_id: str, key: str, team_id: str) -> dict[str, str]:
    if any(not isinstance(x, str) or not x.strip() for x in (device_id, key, team_id)):
        raise ValueError("Faltan identificadores de equipo o sesion")
    return {"accion": "fasesGrupos", "id_dispositivo": device_id, "key": key,
            "id_equipo": team_id}


def schedule_fields(device_id: str, key: str, team_id: str, phases: object,
                    start: date, end: date, round_id: str | None = None) -> dict[str, str]:
    base = phases_fields(device_id, key, team_id)
    if type(start) is not date or type(end) is not date or start > end or (end - start).days > 366:
        raise ValueError("Rango de fechas no valido")
    selected = schedule_selection(phases, round_id)
    base.update({"accion": "horariosJornadas", "id_fase": selected["id_fase"],
                 "id_grupo": selected["id_grupo"], "id_ronda": selected["id_ronda"],
                 "fecha_inicial": start.isoformat() + " 00:00",
                 "fecha_final": end.isoformat() + " 23:59"})
    return base


def standings_fields(device_id: str, key: str, phases: object) -> dict[str, str]:
    if any(not isinstance(x, str) or not x.strip() for x in (device_id, key)):
        raise ValueError("Falta sesion de dispositivo")
    selected = classification_selection(phases)
    return {"accion": "clasificacion", "id_dispositivo": device_id, "key": key,
            "id_grupo": selected["id_grupo"], "tipo_fase": selected["tipo_fase"]}


def post_team_form(fields: dict[str, str]) -> dict:
    """POST explicito, de tamaño limitado, sin registrar respuesta ni credenciales."""
    allowed = {"jugadores": {"accion", "id_dispositivo", "key", "id_equipo"},
               "fasesGrupos": {"accion", "id_dispositivo", "key", "id_equipo"},
               "clasificacion": {"accion", "id_dispositivo", "key", "id_grupo", "tipo_fase"},
               "horariosJornadas": {"accion", "id_dispositivo", "key", "id_equipo",
                                    "id_fase", "id_grupo", "id_ronda", "fecha_inicial", "fecha_final"}}
    action = fields.get("accion") if isinstance(fields, dict) else None
    if not isinstance(action, str) or action not in allowed or set(fields) != allowed[action] or any(not isinstance(x, str) for x in fields.values()):
        raise ValueError("Formulario de equipo no valido")
    optional = {"id_ronda", "id_grupo"} if action == "horariosJornadas" else set()
    if any(not fields[k].strip() for k in allowed[action] - optional):
        raise ValueError("Faltan campos obligatorios")
    if action == "horariosJornadas" and bool(fields["id_grupo"].strip()) == bool(fields["id_ronda"].strip()):
        raise ValueError("Selecciona un grupo o una ronda")
    body = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(TEAM_URL, data=body, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "FBMCard-DEV/0.1"})
    try:
        with open_request(request, timeout=12) as response:
            if response.status != 200:
                raise RuntimeError("Respuesta HTTP de equipo no valida")
            raw = response.read(131073)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("No se pudo consultar el equipo") from None
    if len(raw) > 131072:
        raise RuntimeError("Respuesta de equipo demasiado grande")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise RuntimeError("Respuesta de equipo no es JSON valido") from None
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta de equipo inesperada")
    return data
