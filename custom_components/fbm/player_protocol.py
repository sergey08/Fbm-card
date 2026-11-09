"""FBM Afición 5.0.42 player request form builders (not network transport).

Static DEX evidence: LH5/j;->g: accion=jugadores + id_equipo;
LH5/j;->e: accion=detalleJugador + id_jugador;
LH5/j;->f: accion=buscarJugador + nombre/texto/skip.
The exact endpoint and response models are NOT yet verified for these actions.
"""
from __future__ import annotations


def _session(device_id: str, key: str) -> dict[str, str]:
    if any(type(x) is not str or not x.strip() or len(x) > 1024 for x in (device_id, key)):
        raise ValueError("Sesión técnica no válida")
    return {"id_dispositivo": device_id, "key": key}


def _identifier(value: str) -> str:
    if type(value) is not str or not value.strip() or len(value) > 512:
        raise ValueError("Identificador deportivo no válido")
    return value.strip()


def players_fields(device_id: str, key: str, team_id: str) -> dict[str, str]:
    """Observed APK action for players of an official team."""
    return {"accion": "jugadores", **_session(device_id, key),
            "id_equipo": _identifier(team_id)}


def player_detail_fields(device_id: str, key: str, player_id: str) -> dict[str, str]:
    """Observed APK action for a particular player."""
    return {"accion": "detalleJugador", **_session(device_id, key),
            "id_jugador": _identifier(player_id)}
