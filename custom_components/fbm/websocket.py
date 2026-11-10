"""Puente experimental WebSocket para administradores de Home Assistant."""
from __future__ import annotations

from datetime import date
from .competition_sync import sync_group, preview_group
from .competition_analysis import competition_analysis
from .competition_player_stats import sync_player_stats_batch
from .competition_manager import competition_season_diagnostic
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


async def _player_detail_diagnostic(client, msg):
    player_id = msg["jugador"]
    if type(player_id) is not str or not player_id.strip() or len(player_id) > 512:
        raise ValueError("Jugador no válido")
    return await client.async_player_detail_diagnostic(player_id)


async def _player_statistics(client, msg):
    player_id, team_id = msg["jugador"], msg["equipo"]
    if any(type(v) is not str or not v.strip() or len(v) > 512
           for v in (player_id, team_id)):
        raise ValueError("Identificadores deportivos no válidos")
    return await client.async_player_statistics(player_id, team_id)


async def _player_stats_diagnostic(client, msg):
    player_id, team_id = msg["jugador"], msg["equipo"]
    if any(type(x) is not str or not x.strip() or len(x) > 512
           for x in (player_id, team_id)):
        raise ValueError("Identificadores deportivos no válidos")
    return await client.async_player_statistics_diagnostic(player_id, team_id)


async def _diagnostic(client, msg):
    kind = msg["kind"]
    team_id = msg["equipo"]
    if type(kind) is not str or kind not in ("schedule", "roster"):
        raise ValueError("Diagnóstico no permitido")
    if type(team_id) is not str or not team_id.strip() or len(team_id) > 512:
        raise ValueError("Equipo no válido")
    if kind == "schedule":
        first = date.fromisoformat(msg["desde"])
        last = date.fromisoformat(msg["hasta"])
        return await client.async_team_diagnostic(team_id, kind, first, last)
    return await client.async_team_diagnostic(team_id, kind)


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


@websocket_api.websocket_command({"type": "fbm/player/diagnostic", probatio.Required("entry_id"): str, probatio.Required("jugador"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_player_detail_diagnostic(hass, connection, msg):
    await _dispatch(hass, connection, msg, _player_detail_diagnostic)


@websocket_api.websocket_command({"type": "fbm/player/stats", probatio.Required("entry_id"): str, probatio.Required("jugador"): str, probatio.Required("equipo"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_player_stats(hass, connection, msg):
    await _dispatch(hass, connection, msg, _player_statistics)


@websocket_api.websocket_command({"type": "fbm/player/stats_diagnostic", probatio.Required("entry_id"): str, probatio.Required("jugador"): str, probatio.Required("equipo"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_player_stats_diagnostic(hass, connection, msg):
    await _dispatch(hass, connection, msg, _player_stats_diagnostic)


@websocket_api.websocket_command({"type": "fbm/team/diagnostic", probatio.Required("entry_id"): str, probatio.Required("equipo"): str, probatio.Required("kind"): str, probatio.Required("desde"): str, probatio.Required("hasta"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_diagnostic(hass, connection, msg):
    await _dispatch(hass, connection, msg, _diagnostic)


@websocket_api.websocket_command({"type": "fbm/team/standings", probatio.Required("entry_id"): str, probatio.Required("equipo"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_standings(hass, connection, msg):
    await _dispatch(hass, connection, msg, _standings)



async def _preview_competition(hass, msg):
    client = _client(hass, msg["entry_id"])
    return await preview_group(
        client, msg["equipo"],
        date.fromisoformat(msg["desde"]), date.fromisoformat(msg["hasta"]))


@websocket_api.websocket_command({
    "type": "fbm/competition/preview",
    probatio.Required("entry_id"): str,
    probatio.Required("equipo"): str,
    probatio.Required("desde"): str,
    probatio.Required("hasta"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_competition_preview(hass, connection, msg):
    try:
        result = await _preview_competition(hass, msg)
    except Exception:
        connection.send_error(msg["id"], "fbm_error", "No se pudo consultar el grupo completo.")
        return
    connection.send_result(msg["id"], result)


async def _sync_competition(hass, msg):
    entry_id = msg["entry_id"]
    client = _client(hass, entry_id)
    entry = hass.data[DOMAIN][entry_id]
    archive = await hass.async_add_executor_job(
        entry["competitions_archive_factory"], entry["competitions_sqlite_path"])
    return await sync_group(
        client, archive, msg["equipo"],
        date.fromisoformat(msg["desde"]), date.fromisoformat(msg["hasta"]),
        fetch_rosters=msg["incluir_plantillas"])


@websocket_api.websocket_command({
    "type": "fbm/competition/sync",
    probatio.Required("entry_id"): str,
    probatio.Required("equipo"): str,
    probatio.Required("desde"): str,
    probatio.Required("hasta"): str,
    probatio.Required("incluir_plantillas"): bool,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_competition_sync(hass, connection, msg):
    try:
        result = await _sync_competition(hass, msg)
    except Exception:
        connection.send_error(msg["id"], "fbm_error", "No se pudo sincronizar la competición.")
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    "type": "fbm/competition/list",
    probatio.Required("entry_id"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_competition_list(hass, connection, msg):
    try:
        _client(hass, msg["entry_id"])
        entry = hass.data[DOMAIN][msg["entry_id"]]
        archive = await hass.async_add_executor_job(
            entry["competitions_archive_factory"], entry["competitions_sqlite_path"])
        groups = await hass.async_add_executor_job(archive.followed)
    except Exception:
        connection.send_error(msg["id"], "fbm_error", "No se pudieron leer las competiciones.")
        return
    connection.send_result(msg["id"], {"competitions": groups})


def _offline_team_summary(archive_path, archive_factory, team_id):
    """Return already archived public team competition data, never fetch FBM."""
    from pathlib import Path
    if not Path(archive_path).is_file():
        return {"found": False}
    archive = archive_factory(archive_path)
    matches = []
    for group in archive.followed_with_anchor()[:50]:
        identity = {**{key: group[key] for key in
                       ("season_id", "phase_id", "group_id")},
                    "season_verified": True}
        standings = archive.latest(identity, "standings")
        if not standings or not any(
                type(row) is dict and row.get("id") == team_id
                for row in standings["payload"].get("clasificacion", [])):
            continue
        fixtures = archive.latest(identity, "fixtures")
        matches.append((standings, fixtures))
        if len(matches) > 1:
            # Ambiguous team across seasons/phases: never choose silently.
            return {"found": False}
    if not matches:
        return {"found": False}
    standings, fixtures = matches[0]
    return {
        "found": True,
        "standings": standings["payload"],
        "fixtures": fixtures["payload"] if fixtures else None,
        "observed_at": {
            "standings": standings["observed_at"],
            "fixtures": fixtures["observed_at"] if fixtures else None,
        },
    }


@websocket_api.websocket_command({
    "type": "fbm/competition/team_snapshot",
    probatio.Required("entry_id"): str,
    probatio.Required("equipo"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_competition_team_snapshot(hass, connection, msg):
    """Read public group results from SQLite without network or player data."""
    try:
        _client(hass, msg["entry_id"])
        team = msg["equipo"]
        if type(team) is not str or not team.strip() or len(team) > 512:
            raise ValueError("Invalid team ID")
        entry = hass.data[DOMAIN][msg["entry_id"]]
        result = await hass.async_add_executor_job(
            _offline_team_summary,
            entry["competitions_sqlite_path"],
            entry["competitions_archive_factory"], team)
    except Exception:
        connection.send_error(msg["id"], "fbm_error",
                              "No se pudieron leer los datos archivados del equipo.")
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    "type": "fbm/competition/latest",
    probatio.Required("entry_id"): str,
    probatio.Required("season_id"): str,
    probatio.Required("phase_id"): str,
    probatio.Required("group_id"): str,
    probatio.Required("source"): str,
    probatio.Required("subject"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_competition_latest(hass, connection, msg):
    try:
        _client(hass, msg["entry_id"])
        entry = hass.data[DOMAIN][msg["entry_id"]]
        archive = await hass.async_add_executor_job(
            entry["competitions_archive_factory"], entry["competitions_sqlite_path"])
        identity = {"season_verified": True, "season_id": msg["season_id"],
                    "phase_id": msg["phase_id"], "group_id": msg["group_id"]}
        item = await hass.async_add_executor_job(
            archive.latest, identity, msg["source"], msg["subject"])
    except Exception:
        connection.send_error(msg["id"], "fbm_error", "No se pudieron leer los datos archivados.")
        return
    connection.send_result(msg["id"], {"snapshot": item})



@websocket_api.websocket_command({
    "type": "fbm/competition/analysis",
    probatio.Required("entry_id"): str,
    probatio.Required("season_id"): str,
    probatio.Required("phase_id"): str,
    probatio.Required("group_id"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_competition_analysis(hass, connection, msg):
    """Offline analysis of already stored FBM records, no network calls."""
    try:
        _client(hass, msg["entry_id"])
        entry = hass.data[DOMAIN][msg["entry_id"]]
        archive = await hass.async_add_executor_job(
            entry["competitions_archive_factory"], entry["competitions_sqlite_path"])
        identity = {
            "season_verified": True, "season_id": msg["season_id"],
            "phase_id": msg["phase_id"], "group_id": msg["group_id"],
        }
        standing = await hass.async_add_executor_job(archive.latest, identity, "standings")
        fixtures = await hass.async_add_executor_job(archive.latest, identity, "fixtures")
        if standing is None or fixtures is None:
            raise ValueError("Sin clasificación o calendario archivado")
        rows = standing["payload"].get("clasificacion", [])
        if len(rows) > 100:
            raise ValueError("Demasiados equipos")
        rosters = {}
        for row in rows:
            tid = row.get("id")
            if type(tid) is not str or not tid or len(tid) > 512:
                raise ValueError("Equipo no identificado")
            result = await hass.async_add_executor_job(
                archive.latest, identity, "roster", tid)
            if result is not None:
                rosters[tid] = result["payload"]
        # Admin-only player stats stay outside ordinary HA sensor state.
        individual = {}
        for roster in rosters.values():
            for person in roster.get("jugadores", []):
                pid = person.get("id") if type(person) is dict else None
                if type(pid) is not str:
                    continue
                result = await hass.async_add_executor_job(
                    archive.latest, identity, "player_stats", pid)
                if result is not None:
                    individual[pid] = result["payload"]
        report = await hass.async_add_executor_job(
            competition_analysis, standing["payload"], fixtures["payload"],
            rosters, individual)
        report["observed_at"] = {
            "standings": standing["observed_at"],
            "fixtures": fixtures["observed_at"],
        }
    except Exception:
        connection.send_error(msg["id"], "fbm_error",
                              "No se pudo analizar la competición archivada.")
        return
    connection.send_result(msg["id"], report)



@websocket_api.websocket_command({
    "type": "fbm/competition/player_stats_batch",
    probatio.Required("entry_id"): str,
    probatio.Required("season_id"): str,
    probatio.Required("phase_id"): str,
    probatio.Required("group_id"): str,
    probatio.Required("equipo"): str,
    probatio.Required("offset"): int,
    probatio.Required("limit"): int,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_competition_player_stats_batch(hass, connection, msg):
    """Explicit admin-only bounded update; never returns player identities."""
    try:
        client = _client(hass, msg["entry_id"])
        entry = hass.data[DOMAIN][msg["entry_id"]]
        archive = await hass.async_add_executor_job(
            entry["competitions_archive_factory"],
            entry["competitions_sqlite_path"])
        key = {"season_verified": True,
               "season_id": msg["season_id"],
               "phase_id": msg["phase_id"],
               "group_id": msg["group_id"]}
        result = await sync_player_stats_batch(
            client, archive, key, msg["equipo"],
            offset=msg["offset"], limit=msg["limit"])
    except Exception:
        connection.send_error(msg["id"], "fbm_error",
                              "No se pudieron actualizar las estadísticas.")
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    "type": "fbm/competition/verify_season",
    probatio.Required("entry_id"): str,
    probatio.Required("equipo"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_competition_verify_season(hass, connection, msg):
    """Report only whether 2 independent official team details agree on season."""
    try:
        client = _client(hass, msg["entry_id"])
        result = await competition_season_diagnostic(client, msg["equipo"])
    except Exception:
        connection.send_error(msg["id"], "fbm_error",
                              "No se pudo verificar la temporada de la competición.")
        return
    connection.send_result(msg["id"], result)

def async_register_commands(hass):
    for command in (ws_entries, ws_status, ws_create, ws_register, ws_recover, ws_connect, ws_search, ws_schedule, ws_phases, ws_schedule_round, ws_standings, ws_group_identity, ws_schedule_probe, ws_roster, ws_player_detail, ws_player_stats, ws_diagnostic, ws_player_detail_diagnostic, ws_player_stats_diagnostic, ws_competition_sync, ws_competition_list, ws_competition_team_snapshot, ws_competition_latest, ws_competition_preview, ws_competition_analysis, ws_competition_verify_season, ws_competition_player_stats_batch):
        websocket_api.async_register_command(hass, command)


