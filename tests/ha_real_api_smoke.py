"""Real Home Assistant 2026.11 API smoke test, not a simulated HA stub.

Run in a separate fresh Python environment with homeassistant==2026.11.0.
No HA server is launched, no secrets or real FBM network is accessed.
"""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import tempfile

import probatio
from homeassistant import config_entries
from homeassistant.core import callback

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "fbm"
PACKAGE = "fbm_ha_core_smoke"
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = pkg

for name in ("const", "config_flow"):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{name}", ROOT / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

flow_module = sys.modules[f"{PACKAGE}.config_flow"]


async def run():
    assert issubclass(flow_module.FBMConfigFlow, config_entries.ConfigFlow)
    assert issubclass(flow_module.FBMCompetitionOptionsFlow, config_entries.OptionsFlow)
    flow = flow_module.FBMConfigFlow.async_get_options_flow(None)
    assert isinstance(flow, config_entries.OptionsFlow)

    menu = await flow.async_step_init()
    assert menu["type"] == "menu", menu
    assert menu["step_id"] == "init", menu
    assert menu["menu_options"] == ["search", "manage", "refresh", "automatic"], menu

    # Fail locally: no injected HA instance, client, credentials or network.
    invalid_search = await flow.async_step_search({"texto": "ab"})
    assert invalid_search["type"] == "form", invalid_search
    assert invalid_search["errors"]["base"] == "invalid_search"
    assert isinstance(invalid_search["data_schema"], probatio.Schema)

    # The actual 2026.11 schema must accept an explicitly enabled
    # group+player opt-in, but neither should start from an ordinary menu.
    assert "automatic" in menu["menu_options"]
    bad_confirm = await flow.async_step_confirm()
    assert bad_confirm["type"] == "form"
    assert bad_confirm["step_id"] == "search"
    # Exercise the actual Home Assistant flow result classes and Probatio
    # schemas with a fake FBM transport and a temporary real SQLite archive.
    # No test account, network request, deployment or production mutations.
    from datetime import date
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.competition_archive", ROOT / "competition_archive.py"
    )
    archive_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = archive_module
    spec.loader.exec_module(archive_module)
    Archive = archive_module.CompetitionArchive

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def async_search_teams(self, query, skip):
            self.calls.append("search")
            return [{"id": "pinto", "nombre": "Equipo ficticio",
                     "categoria": "Alevin", "temporada": "26/27"}]

        async def async_team_group_identity(self, team_id):
            self.calls.append("identity")
            return {"phase_id": "phase", "group_id": "group",
                    "season_verified": False}

        async def async_team_standings(self, team_id):
            self.calls.append("standings")
            return {"clasificacion": [{"id": "pinto"}, {"id": "rival"}]}

        async def async_verify_group_season(self, team_ids):
            self.calls.append("verify")
            return {"season_verified": True, "season_id": "26/27"}

        async def async_team_schedule(self, team_id, start, end):
            self.calls.append("schedule")
            return {"partidos": [{
                "id": "m1", "local": "A", "visitante": "B",
                "fecha": "2026-11-01", "estado": "finished",
                "marcador": {"local": 35, "visitante": 31},
            }]}

        async def async_team_roster(self, team_id):
            self.calls.append("roster")
            return {"jugadores": [{"id": "player", "nombre": "No real"}]}

    class FakeConfigEntries:
        def __init__(self, entry):
            self.entry = entry

        def async_get_known_entry(self, entry_id):
            assert entry_id == self.entry.entry_id
            return self.entry

    class FakeHass:
        def __init__(self, db_path, client):
            self.config_entries = FakeConfigEntries(
                types.SimpleNamespace(entry_id="test-entry", options={}))
            self.data = {"fbm": {"test-entry": {
                "cliente_independiente": client,
                "competitions_sqlite_path": str(db_path),
                "competitions_archive_factory": Archive,
            }}}

        def verify_event_loop_thread(self, operation):
            assert operation == "async_dispatcher_send"

        async def async_add_executor_job(self, callback, *args):
            return callback(*args)

    with tempfile.TemporaryDirectory() as folder:
        db = Path(folder) / "competition.sqlite"
        client = FakeClient()
        flow.hass = FakeHass(db, client)
        # HA 2026.11 exposes config_entry as a read-only property resolved
        # through hass.config_entries and the flow's handler entry ID.
        flow.handler = "test-entry"
        search = await flow.async_step_search({"texto": "pinto"})
        assert search["step_id"] == "select", search
        select = await flow.async_step_select({"equipo": "pinto"})
        assert select["step_id"] == "confirm", select
        assert not db.exists(), "preview must not persist without consent"
        followed = await flow.async_step_confirm({"confirmar": True})
        assert followed["type"] == "create_entry", followed
        assert Archive(str(db)).followed_with_anchor()[0]["anchor_team_id"] == "pinto"
        assert "schedule" in client.calls
        assert client.calls.count("roster") == 2

        settings = await flow.async_step_automatic()
        assert settings["step_id"] == "automatic"
        assert isinstance(settings["data_schema"], probatio.Schema)
        blocked = await flow.async_step_automatic(
            {"auto_groups": False, "auto_players": True})
        assert blocked["errors"]["base"] == "auto_requires_groups"
        opted_in = await flow.async_step_automatic(
            {"auto_groups": True, "auto_players": True})
        assert opted_in["type"] == "create_entry"
        assert opted_in["data"] == {
            "auto_groups": True, "auto_players": True}
        scheduler_spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.competition_auto_sync",
            ROOT / "competition_auto_sync.py")
        scheduler = importlib.util.module_from_spec(scheduler_spec)
        sys.modules[scheduler_spec.name] = scheduler
        scheduler_spec.loader.exec_module(scheduler)
        assert scheduler.GROUP_INTERVAL.total_seconds() == 4 * 3600
        assert scheduler.PLAYER_INTERVAL.total_seconds() == 2 * 3600
        assert scheduler.PLAYER_CYCLE_DELAY.total_seconds() == 24 * 3600

        client.calls.clear()
        offered = await flow.async_step_refresh()
        assert offered["step_id"] == "refresh", offered
        choice = await flow.async_step_refresh({"competicion": "0"})
        assert choice["step_id"] == "refresh_confirm", choice
        assert "roster" not in client.calls
        refreshed = await flow.async_step_refresh_confirm({"confirmar": True})
        assert refreshed["type"] == "create_entry", refreshed
        assert "schedule" in client.calls
        assert "roster" not in client.calls
        identity = {"season_verified": True, "season_id": "26/27",
                    "phase_id": "phase", "group_id": "group"}
        assert Archive(str(db)).latest(identity, "fixtures") is not None

        # The summary entity must use actual HA SensorEntity and expose
        # only public team standings/results, not player/roster data.
        sensor_spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.sensor", ROOT / "sensor.py")
        sensor_module = importlib.util.module_from_spec(sensor_spec)
        sys.modules[sensor_spec.name] = sensor_module
        sensor_spec.loader.exec_module(sensor_module)
        from homeassistant.components.sensor import SensorEntity
        assert issubclass(sensor_module.FBMCompetitionsSensor, SensorEntity)
        summary = sensor_module._read_competition_summary(str(db))
        assert summary["count"] == 1
        assert len(summary["groups"][0]["ranking"]) == 2
        assert summary["groups"][0]["recent_results"][0]["marcador"] == {
            "local": 35, "visitante": 31}
        assert "jugadores" not in str(summary)
        assert "roster" not in str(summary)

        listed = await flow.async_step_manage()
        assert listed["step_id"] == "manage", listed
        to_unfollow = await flow.async_step_manage({"competicion": "0"})
        assert to_unfollow["step_id"] == "unfollow", to_unfollow
        stopped = await flow.async_step_unfollow({"confirmar": True})
        assert stopped["type"] == "create_entry", stopped
        assert not Archive(str(db)).followed()
        assert Archive(str(db)).latest(identity, "fixtures") is not None
    print("PASS: actual HA OptionsFlow search/follow/refresh/unfollow + temporary SQLite")
    print("PASS: real HA OptionsFlow factory/menu and Probatio form validation")


if __name__ == "__main__":
    asyncio.run(run())
