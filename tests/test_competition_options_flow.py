"""Offline end-to-end flow tests for the HA native competition manager.

Uses a minimal HA-flow stub; no Home Assistant install, FBM credentials or
requests to the production integration. Persistent DB assertions use temp paths.
"""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"
PREFIX = "fbm_options_flow_test_pkg"
pkg = types.ModuleType(PREFIX)
pkg.__path__ = [str(ROOT)]
sys.modules[PREFIX] = pkg

# The HA component stub is loaded once at collection time; it does not need
# any real Home Assistant server or credentials.
ha = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
entries = sys.modules.setdefault(
    "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries"))


class ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

class OptionsFlow:
    @staticmethod
    def async_show_menu(**kwargs):
        return {"type": "menu", **kwargs}

    @staticmethod
    def async_show_form(**kwargs):
        return {"type": "form", **kwargs}

    @staticmethod
    def async_abort(**kwargs):
        return {"type": "abort", **kwargs}

    @staticmethod
    def async_create_entry(**kwargs):
        return {"type": "create_entry", **kwargs}

entries.ConfigFlow = ConfigFlow
entries.OptionsFlow = OptionsFlow
ha.config_entries = entries

probatio = sys.modules.setdefault("probatio", types.ModuleType("probatio"))
probatio.Required = lambda name, default=None: name
probatio.In = lambda options: options
probatio.Schema = lambda schema: schema


def import_part(name):
    spec = importlib.util.spec_from_file_location(
        PREFIX + "." + name, ROOT / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

archive_module = import_part("competition_archive")
import_part("const")
import_part("competition_manager")
flow_module = import_part("config_flow")
Archive = archive_module.CompetitionArchive


class FakeClient:
    def __init__(self, verified=True):
        self.verified = verified
        self.calls = []

    async def async_search_teams(self, query, skip):
        self.calls.append("search")
        return [{"id": "team-A", "nombre": "Pinto Basket", "categoria": "Alevin", "temporada": "26/27"}]

    async def async_team_group_identity(self, team):
        self.calls.append("identity")
        return {"phase_id": "phase", "group_id": "group", "season_verified": False}

    async def async_team_standings(self, team):
        self.calls.append("standings")
        return {"clasificacion": [{"id": "team-A"}, {"id": "team-B"}]}

    async def async_verify_group_season(self, teams):
        self.calls.append("season")
        return {"season_verified": self.verified,
                "season_id": "verified-season" if self.verified else None}


class FakeHass:
    def __init__(self, path, client):
        self.data = {"fbm": {"entry-1": {
            "cliente_independiente": client,
            "competitions_sqlite_path": str(path),
            "competitions_archive_factory": Archive,
        }}}

    async def async_add_executor_job(self, func, *args):
        return func(*args)


class OptionsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "competition.sqlite"
        self.client = FakeClient()
        self.flow = flow_module.FBMConfigFlow.async_get_options_flow(None)
        self.flow.hass = FakeHass(self.path, self.client)
        self.flow.config_entry = types.SimpleNamespace(entry_id="entry-1", options={})

    async def test_search_confirm_then_manage_and_unfollow_preserves_archive(self):
        self.assertEqual((await self.flow.async_step_init())["type"], "menu")
        result = await self.flow.async_step_search({"texto": "pinto"})
        self.assertEqual(result["step_id"], "select")
        result = await self.flow.async_step_select({"equipo": "team-A"})
        self.assertEqual(result["step_id"], "confirm")
        self.assertFalse(self.path.exists(), "selection preview must not write SQLite")
        result = await self.flow.async_step_confirm({"confirmar": True})
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(len(Archive(str(self.path)).followed()), 1)
        selection = {"season_id": "verified-season", "phase_id": "phase",
                     "group_id": "group", "season_verified": True}
        Archive(str(self.path)).record(
            selection, "standings", {"clasificacion": [{"id": "team-A"}]})
        result = await self.flow.async_step_manage()
        self.assertEqual(result["step_id"], "manage")
        result = await self.flow.async_step_manage({"competicion": "0"})
        self.assertEqual(result["step_id"], "unfollow")
        self.assertEqual(len(Archive(str(self.path)).followed()), 1)
        result = await self.flow.async_step_unfollow({"confirmar": True})
        self.assertEqual(result["type"], "create_entry")
        archive = Archive(str(self.path))
        self.assertEqual(archive.followed(), [])
        self.assertIsNotNone(archive.latest(selection, "standings"))
        self.assertNotIn("roster", self.client.calls)

    async def test_invalid_season_never_writes_competition(self):
        self.client.verified = False
        await self.flow.async_step_search({"texto": "pinto"})
        result = await self.flow.async_step_select({"equipo": "team-A"})
        self.assertEqual(result["errors"]["base"], "season_unverified")
        result = await self.flow.async_step_confirm({"confirmar": True})
        self.assertEqual(result["errors"]["base"], "season_unverified")
        self.assertFalse(self.path.exists())
        self.assertNotIn("roster", self.client.calls)

    async def test_invalid_selection_and_empty_manage_are_safe(self):
        await self.flow.async_step_search({"texto": "pinto"})
        result = await self.flow.async_step_select({"equipo": "untrusted-team"})
        self.assertEqual(result["errors"]["base"], "invalid_selection")
        self.assertEqual((await self.flow.async_step_manage())["reason"], "none_followed")
        self.assertFalse(self.path.exists())

if __name__ == "__main__":
    unittest.main()
