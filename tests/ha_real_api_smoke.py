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
    assert menu["menu_options"] == ["search", "manage", "refresh"], menu

    # Fail locally: no injected HA instance, client, credentials or network.
    invalid_search = await flow.async_step_search({"texto": "ab"})
    assert invalid_search["type"] == "form", invalid_search
    assert invalid_search["errors"]["base"] == "invalid_search"
    assert isinstance(invalid_search["data_schema"], probatio.Schema)

    bad_confirm = await flow.async_step_confirm()
    assert bad_confirm["type"] == "form"
    assert bad_confirm["step_id"] == "search"
    print("PASS: real HA OptionsFlow factory/menu and Probatio form validation")


if __name__ == "__main__":
    asyncio.run(run())
