"""Verify clean onboarding, restart and upgrade in isolated HA Core processes."""
import asyncio
from datetime import date
import json
from time import monotonic
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch
from urllib.error import URLError

from homeassistant import loader
from homeassistant.bootstrap import async_from_config_dict
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "fbm"


async def run(folder, phase):
    hass = HomeAssistant(str(folder))
    loader.async_setup(hass)
    sys.path.insert(0, str(folder))
    from custom_components.fbm import aficion_adapter, independent_client
    from custom_components.fbm import guest_session

    calls = []
    offline = phase == "upgrade"

    def device_response(fields):
        action = fields["accion"]
        calls.append(action)
        if action == "registrar":
            assert phase in ("install", "stable"), "unexpected second registration"
        else:
            assert action == "acceso"
            assert fields["id_dispositivo"] == "isolated-fbm-device"
        if offline:
            raise URLError("simulated connection outage")
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
            if phase in ("install", "stable"):
                assert not entries.async_entries(DOMAIN)
                form = await entries.flow.async_init(DOMAIN, context={"source": "user"})
                assert form["step_id"] == "user", form
                created = await entries.flow.async_configure(form["flow_id"], {})
                assert created["type"] == "create_entry", created
                await hass.async_block_till_done()
            entry, = entries.async_entries(DOMAIN)
            assert entry.state.value == "loaded", entry.state
            if phase in ("install", "stable"):
                options = entries.options
                result = await options.async_init(entry.entry_id)
                flow_id = result["flow_id"]
                steps = [
                    ("search", {"next_step_id": "search"}),
                    ("select", {"texto": "Test Team"}),
                    ("confirm", {"equipo": "test-team"}),
                ]
                if phase == "stable":
                    client = hass.data[DOMAIN][entry.entry_id]["cliente_independiente"]
                    await client.async_create_identity()
                    await client.async_register("16")
                    await client.async_connect("16")
                else:
                    steps[:1] = [
                        ("guest", {"next_step_id": "search"}),
                        ("search", {"autorizar": True}),
                    ]
                for expected, data in steps:
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
            card_url = hass.data.get("fbm_card_url", "/fbm_static/fbm-card.js")
            matching = [item for item in resources.async_items()
                        if item["url"].split("?", 1)[0] == card_url]
            assert len(matching) == 1, matching
            archive = hass.data[DOMAIN][entry.entry_id]
            if phase == "upgrade":
                client = archive["cliente_independiente"]
                assert not (await client.async_status())["sesion_vigente"]
                try:
                    await client.async_search_teams("Test Team")
                except aficion_adapter.FBMAccessNotValidated:
                    pass
                else:
                    raise AssertionError("search unexpectedly succeeded during outage")
                assert calls == ["acceso"], calls
                offline = False
                with patch.object(independent_client, "monotonic", return_value=monotonic() + 31):
                    assert (await client.async_search_teams("Test Team"))[0]["id"] == "test-team"
                assert calls == ["acceso", "acceso"], calls
            identity = await archive["identidad_independiente"].async_load()
            snapshot = [entry.entry_id, entity_id, unique_id, identity.uid, matching[0]["id"]]
            marker = folder / "lifecycle-test.json"
            if phase in ("install", "stable"):
                await hass.async_add_executor_job(marker.write_text, json.dumps(snapshot), "utf-8")
            else:
                saved = await hass.async_add_executor_job(marker.read_text, "utf-8")
                assert json.loads(saved) == snapshot
            print(f"PASS: isolated Home Assistant Core {phase}")
        finally:
            await hass.async_stop()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        asyncio.run(run(Path(sys.argv[1]), sys.argv[2]))
    else:
        stable = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else None
        candidate = ROOT / "custom_components" / DOMAIN
        scenarios = [[(candidate, "install"), (candidate, "restart")]]
        if stable is not None:
            scenarios.append([(stable, "stable"), (candidate, "upgrade")])
        for scenario in scenarios:
            with tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                destination = folder / "custom_components" / DOMAIN
                for source, phase in scenario:
                    if destination.exists():
                        shutil.rmtree(destination)
                    shutil.copytree(source, destination)
                    subprocess.run([sys.executable, __file__, temp, phase],
                                   check=True, timeout=180)
