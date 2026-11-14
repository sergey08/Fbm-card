"""Boot isolated HA Core twice and verify first-team onboarding and persistence."""
import asyncio
from datetime import date
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch

from homeassistant.bootstrap import async_from_config_dict
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "fbm"


async def run(folder, phase):
    hass = HomeAssistant(str(folder))
    sys.path.insert(0, str(folder))
    from custom_components.fbm import aficion_adapter, independent_client
    from custom_components.fbm import guest_session

    calls = []

    def device_response(fields):
        action = fields["accion"]
        calls.append(action)
        if action == "registrar":
            assert phase == "install", "unexpected registration after restart"
        else:
            assert action == "acceso"
            assert fields["id_dispositivo"] == "isolated-fbm-device"
        return {"error": "", "key": "fixture-key", "id_dispositivo": "isolated-fbm-device"}

    async def search(adapter, query, skip):
        return [{"id": "test-team", "nombre": "Test Team", "temporada": "26/27"}]

    async def group(adapter, team):
        return {"phase_id": "test-phase", "group_id": "test-group"}

    async def standings(adapter, team):
        return {"clasificacion": [{"id": "test-team"}, {"id": "test-rival"}]}

    async def schedule(adapter, team, start, end):
        return {"partidos": [{"id": "test-game", "local": "Test Team",
                              "visitante": "Test Rival", "fecha": date.today().isoformat(),
                              "estado": "finished", "marcador": {"local": 45, "visitante": 40}}]}

    async def roster(adapter, team):
        return {"jugadores": [{"id": "fixture-player", "nombre": "Fixture Player"}]}

    adapter = aficion_adapter.AficionFBMAdapter
    with (
        patch.object(independent_client, "post_device_form", device_response),
        patch.object(guest_session, "post_device_form", device_response),
        patch.object(adapter, "search_teams", search),
        patch.object(adapter, "team_group_identity", group),
        patch.object(adapter, "team_standings", standings),
        patch.object(adapter, "team_schedule", schedule),
        patch.object(adapter, "team_roster", roster),
    ):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        assert await async_from_config_dict(
            {"http": {"server_host": "127.0.0.1", "server_port": port}, "lovelace": {}},
            hass,
        ) is hass
        await hass.async_start()
        try:
            entries = hass.config_entries
            if phase == "install":
                assert not entries.async_entries(DOMAIN)
                form = await entries.flow.async_init(DOMAIN, context={"source": "user"})
                assert form["step_id"] == "user", form
                created = await entries.flow.async_configure(form["flow_id"], {})
                assert created["type"] == "create_entry", created
                await hass.async_block_till_done()
            entry, = entries.async_entries(DOMAIN)
            assert entry.state.value == "loaded", entry.state
            if phase == "install":
                options = entries.options
                result = await options.async_init(entry.entry_id)
                flow_id = result["flow_id"]
                for expected, data in (
                    ("guest", {"next_step_id": "search"}),
                    ("search", {"autorizar": True}),
                    ("select", {"texto": "Test Team"}),
                    ("confirm", {"equipo": "test-team"}),
                ):
                    result = await options.async_configure(flow_id, data)
                    assert result["step_id"] == expected, result
                    if expected == "guest":
                        assert not calls, calls
                result = await options.async_configure(flow_id, {"confirmar": True})
                assert result["type"] == "create_entry", result
                assert calls == ["registrar", "acceso"], calls
            else:
                assert calls == ["acceso"], calls

            await hass.async_block_till_done()
            unique_id = f"fbm_{entry.entry_id}_competitions"
            registry = entity_registry.async_get(hass)
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            assert entity_id is not None
            await hass.services.async_call(
                "homeassistant", "update_entity", {"entity_id": entity_id}, blocking=True,
            )
            await hass.async_block_till_done()
            assert hass.states.get(entity_id).state == "1", hass.states.get(entity_id)
            resources = hass.data["lovelace"].resources
            matching = [item for item in resources.async_items()
                        if item["url"].split("?")[0] == "/fbm_static/fbm-card.js"]
            assert len(matching) == 1, matching
            archive = hass.data[DOMAIN][entry.entry_id]
            identity = await archive["identidad_independiente"].async_load()
            snapshot = [entry.entry_id, entity_id, unique_id, identity.uid, matching[0]["id"]]
            marker = folder / "lifecycle-test.json"
            if phase == "install":
                marker.write_text(json.dumps(snapshot), encoding="utf-8")
            else:
                assert json.loads(marker.read_text(encoding="utf-8")) == snapshot
            print(f"PASS: isolated Home Assistant Core {phase}")
        finally:
            await hass.async_stop()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        asyncio.run(run(Path(sys.argv[1]), sys.argv[2]))
    else:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            shutil.copytree(ROOT / "custom_components" / DOMAIN,
                            folder / "custom_components" / DOMAIN)
            for phase in ("install", "restart"):
                subprocess.run([sys.executable, __file__, temp, phase],
                               check=True, timeout=180)
