"""Offline tests for the minimal FBM competition HA sensor."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, MagicMock

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "fbm"
module_ha = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
sys.modules.setdefault("homeassistant.components", types.ModuleType("homeassistant.components"))
sensor_mod = types.ModuleType("homeassistant.components.sensor")
sensor_mod.SensorEntity = type("SensorEntity", (), {})
sys.modules["homeassistant.components.sensor"] = sensor_mod
core_mod = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
core_mod.HomeAssistant = object
config_mod = sys.modules.setdefault("homeassistant.config_entries", types.ModuleType("homeassistant.config_entries"))
config_mod.ConfigEntry = object

pkg_name = "fbm_sensor_test_pkg"
pkg = types.ModuleType(pkg_name)
pkg.__path__ = [str(PKG)]
sys.modules[pkg_name] = pkg
for name in ("const", "competition_archive", "sensor"):
    spec = importlib.util.spec_from_file_location(pkg_name + "." + name, PKG / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

Sensor = sys.modules[pkg_name + ".sensor"]
Archive = sys.modules[pkg_name + ".competition_archive"].CompetitionArchive


class SensorTests(unittest.IsolatedAsyncioTestCase):
    async def test_does_not_create_database_or_contact_fbm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "absent.db")
            self.assertEqual(Sensor._read_competition_summary(path),
                             {"count": 0, "groups": []})
            self.assertFalse(Path(path).exists())

    async def test_summarizes_archived_groups_without_player_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "archive.db")
            archive = Archive(path)
            identity = {"season_verified": True, "season_id": "season",
                        "phase_id": "phase", "group_id": "group"}
            archive.follow(identity)
            archive.record(identity, "standings", {"clasificacion": [
                {"id": "team1", "equipo": "Team", "escudo": "PRIVATE_IMAGE"}]})
            archive.record(identity, "fixtures", {"partidos": [
                {"id": "game1", "local": "Team", "visitante": "Other"}]})
            archive.record(identity, "roster", {"jugadores": [
                {"id": "player", "nombre": "PRIVATE_CHILD", "foto": "PRIVATE_IMAGE"}]},
                subject="team1")
            summary = Sensor._read_competition_summary(path, Archive)
            self.assertEqual(summary["count"], 1)
            self.assertEqual(summary["groups"][0]["teams"], 1)
            self.assertEqual(summary["groups"][0]["matches"], 1)
            self.assertNotIn("PRIVATE_CHILD", str(summary))
            self.assertNotIn("PRIVATE_IMAGE", str(summary))

            class Hass:
                data = {"fbm": {"entry": {
                    "competitions_sqlite_path": path,
                    "competitions_archive_factory": Archive}}}
                async def async_add_executor_job(self, fn, *args):
                    return fn(*args)

            sensor = Sensor.FBMCompetitionsSensor(Hass(), types.SimpleNamespace(entry_id="entry"))
            await sensor.async_update()
            self.assertTrue(sensor._attr_available)
            self.assertEqual(sensor._attr_native_value, 1)
            self.assertEqual(sensor._attr_unique_id, "fbm_entry_competitions")

    async def test_missing_config_entry_marks_unavailable(self):
        class Hass:
            data = {"fbm": {}}
        sensor = Sensor.FBMCompetitionsSensor(Hass(), types.SimpleNamespace(entry_id="entry"))
        await sensor.async_update()
        self.assertFalse(sensor._attr_available)


if __name__ == "__main__":
    unittest.main()
