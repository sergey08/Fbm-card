"""Puente experimental WebSocket para administradores de Home Assistant."""
from __future__ import annotations

from datetime import date
import probatio
from homeassistant.components import websocket_api

from .const import DOMAIN


def _client(hass, entry_id):
    if not isinstance(entry_id, str) or not entry_id or len(entry_id) > 128:
        raise ValueError("Entrada no valida")
    entry = hass.data.get(DOMAIN, {}).get(entry_id)
    if not isinstance(entry, dict) or "cliente_independiente" not in entry:
        raise ValueError("Entrada FBM no disponible")
    return entry["cliente_independiente"]


async def _dispatch(hass, connection, msg, operation):
    """Devuelve solo datos normalizados y errores genericos sin credenciales."""
    try:
        client = _client(hass, msg["entry_id"])
        result = await operation(client, msg)
    except Exception:  # No exponer excepciones de red o almacenamiento al cliente.
        connection.send_error(msg["id"], "fbm_error", "No se pudo completar la operacion FBM.")
        return
    connection.send_result(msg["id"], result)


async def _status(client, msg):
    return await client.async_status()


async def _create(client, msg):
    await client.async_create_identity()
    return {"identidad_creada": True}


def _release(msg):
    release = msg["android_release"]
    if not isinstance(release, str) or not release.strip() or len(release) > 32:
        raise ValueError("Perfil Android no valido")
    return release.strip()


async def _register(client, msg):
    await client.async_register(_release(msg))
    return {"candidato_guardado": True}


async def _recover(client, msg):
    await client.async_recover_registration(_release(msg))
    return {"candidato_guardado": True}


async def _connect(client, msg):
    await client.async_connect(_release(msg))
    return {"sesion_en_memoria": True}


async def _search(client, msg):
    text, skip = msg["texto"], msg["skip"]
    if not isinstance(text, str) or not text.strip() or len(text) > 100 or type(skip) is not int or not 0 <= skip <= 10000:
        raise ValueError("Busqueda no valida")
    return {"equipos": await client.async_search_teams(text.strip(), skip)}


async def _schedule(client, msg):
    team_id, first, last = msg["equipo"], msg["desde"], msg["hasta"]
    if not isinstance(team_id, str) or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no valido")
    if not isinstance(first, str) or not isinstance(last, str) or len(first) != 10 or len(last) != 10:
        raise ValueError("Fecha no valida")
    return await client.async_team_schedule(team_id, date.fromisoformat(first), date.fromisoformat(last))


async def _schedule_probe(client, msg):
    """Read-only response-shape diagnostic using the same official API request."""
    team_id, first, last = msg["equipo"], msg["desde"], msg["hasta"]
    if not isinstance(team_id, str) or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no valido")
    if any(not isinstance(x, str) or len(x) != 10 for x in (first, last)):
        raise ValueError("Fecha no valida")
    return await client.async_team_schedule_probe(
        team_id, date.fromisoformat(first), date.fromisoformat(last))


async def _phases(client, msg):
    team_id = msg["equipo"]
    if not isinstance(team_id, str) or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no valido")
    return await client.async_team_phase_options(team_id)


async def _group_identity(client, msg):
    team_id = msg["equipo"]
    if not isinstance(team_id, str) or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no válido")
    # Read-only official lookup. Never follows groups or creates entities.
    return await client.async_team_group_identity(team_id)


async def _roster(client, msg):
    team_id = msg["equipo"]
    if not isinstance(team_id, str) or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no válido")
    return await client.async_team_roster(team_id)


async def _player_detail(client, msg):
    player_id = msg["jugador"]
    if type(player_id) is not str or not player_id.strip() or len(player_id) > 512:
        raise ValueError("Jugador no válido")
    return await client.async_player_detail(player_id)


async def _standings(client, msg):
    team_id = msg["equipo"]
    if not isinstance(team_id, str) or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no valido")
    return await client.async_team_standings(team_id)


async def _schedule_round(client, msg):
    team_id, round_id, first, last = msg["equipo"], msg["ronda"], msg["desde"], msg["hasta"]
    if any(not isinstance(x, str) or not x.strip() or len(x) > 512 for x in (team_id, round_id)):
        raise ValueError("Equipo o ronda no validos")
    if not isinstance(first, str) or not isinstance(last, str) or len(first) != 10 or len(last) != 10:
        raise ValueError("Fecha no valida")
    return await client.async_team_schedule(team_id, date.fromisoformat(first), date.fromisoformat(last), round_id)


@websocket_api.websocket_command({"type": "fbm/client/entries"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_entries(hass, connection, msg):
    entries = hass.data.get(DOMAIN, {})
    if not isinstance(entries, dict):
        connection.send_error(msg["id"], "fbm_error", "No se pudo consultar la integracion FBM.")
        return
    ids = [key for key, value in entries.items() if isinstance(key, str) and isinstance(value, dict) and "cliente_independiente" in value]
    connection.send_result(msg["id"], {"entries": ids})


@websocket_api.websocket_command({"type": "fbm/client/status", probatio.Required("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_status(hass, connection, msg):
    await _dispatch(hass, connection, msg, _status)


@websocket_api.websocket_command({"type": "fbm/client/create_identity", probatio.Required("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_create(hass, connection, msg):
    await _dispatch(hass, connection, msg, _create)


@websocket_api.websocket_command({"type": "fbm/client/register", probatio.Required("entry_id"): str, probatio.Required("android_release"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_register(hass, connection, msg):
    await _dispatch(hass, connection, msg, _register)


@websocket_api.websocket_command({"type": "fbm/client/recover_registration", probatio.Required("entry_id"): str, probatio.Required("android_release"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_recover(hass, connection, msg):
    await _dispatch(hass, connection, msg, _recover)


@websocket_api.websocket_command({"type": "fbm/client/connect", probatio.Required("entry_id"): str, probatio.Required("android_release"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_connect(hass, connection, msg):
    await _dispatch(hass, connection, msg, _connect)


@websocket_api.websocket_command({"type": "fbm/team/search", probatio.Required("entry_id"): str, probatio.Required("texto"): str, probatio.Required("skip"): int})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_search(hass, connection, msg):
    await _dispatch(hass, connection, msg, _search)


@websocket_api.websocket_command({"type": "fbm/team/schedule", probatio.Required("entry_id"): str, probatio.Required("equipo"): str, probatio.Required("desde"): str, probatio.Required("hasta"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_schedule(hass, connection, msg):
    await _dispatch(hass, connection, msg, _schedule)


@websocket_api.websocket_command({"type": "fbm/team/schedule_probe", probatio.Required("entry_id"): str, probatio.Required("equipo"): str, probatio.Required("desde"): str, probatio.Required("hasta"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_schedule_probe(hass, connection, msg):
    await _dispatch(hass, connection, msg, _schedule_probe)


@websocket_api.websocket_command({"type": "fbm/team/phases", probatio.Required("entry_id"): str, probatio.Required("equipo"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_phases(hass, connection, msg):
    await _dispatch(hass, connection, msg, _phases)


@websocket_api.websocket_command({"type": "fbm/team/schedule_round", probatio.Required("entry_id"): str, probatio.Required("equipo"): str, probatio.Required("ronda"): str, probatio.Required("desde"): str, probatio.Required("hasta"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_schedule_round(hass, connection, msg):
    await _dispatch(hass, connection, msg, _schedule_round)


@websocket_api.websocket_command({"type": "fbm/team/group_identity", probatio.Required("entry_id"): str, probatio.Required("equipo"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_group_identity(hass, connection, msg):
    await _dispatch(hass, connection, msg, _group_identity)


@websocket_api.websocket_command({"type": "fbm/team/players", probatio.Required("entry_id"): str, probatio.Required("equipo"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_roster(hass, connection, msg):
    await _dispatch(hass, connection, msg, _roster)


@websocket_api.websocket_command({"type": "fbm/player/detail", probatio.Required("entry_id"): str, probatio.Required("jugador"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_player_detail(hass, connection, msg):
    await _dispatch(hass, connection, msg, _player_detail)


@websocket_api.websocket_command({"type": "fbm/team/standings", probatio.Required("entry_id"): str, probatio.Required("equipo"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_standings(hass, connection, msg):
    await _dispatch(hass, connection, msg, _standings)


def async_register_commands(hass):
    for command in (ws_entries, ws_status, ws_create, ws_register, ws_recover, ws_connect, ws_search, ws_schedule, ws_phases, ws_schedule_round, ws_standings, ws_group_identity, ws_schedule_probe, ws_roster, ws_player_detail):
        websocket_api.async_register_command(hass, command)


