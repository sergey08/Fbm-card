"""Offline tests for the minimal FBM competition HA sensor."""
from datetime import date, datetime
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
core_mod.callback = lambda fn: fn
config_mod = sys.modules.setdefault("homeassistant.config_entries", types.ModuleType("homeassistant.config_entries"))
config_mod.ConfigEntry = object

dispatcher_mod = sys.modules.setdefault(
    "homeassistant.helpers.dispatcher",
    types.ModuleType("homeassistant.helpers.dispatcher"))
registered=[]
def connect(hass, signal, callback):
    registered.append((signal,callback))
    return lambda: None
dispatcher_mod.async_dispatcher_connect=connect

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
    def test_recent_results_only_use_latest_round_with_a_score(self):
        final = {"estado": "finished", "marcador": {"local": 0, "visitante": 8}}
        matches = [
            {**final, "jornada": 4, "fecha": "2026-11-16"},
            {**final, "jornada": 5, "fecha": "2026-11-14"},
            {**final, "jornada": "5", "fecha": "2026-11-15"},
            {"estado": "scheduled", "jornada": 6},
        ]
        results = Sensor._latest_round_results(matches)
        self.assertEqual([row["jornada"] for row in results], [5, 5])

    def test_upcoming_excludes_past_started_and_duplicate_fixtures(self):
        now = datetime(2026, 11, 16, 12)
        base = {"id": "m1", "local": "A", "visitante": "B", "estado": "scheduled",
                "fecha": "16/11/2026", "hora": "13:00", "campo": "Pabellón"}
        fixtures = [base, base, {**base, "id": "past", "hora": "11:00"},
                    {**base, "id": "finished", "estado": "finished"},
                    {**base, "id": "m2", "fecha": "2026-11-17", "hora": None}]
        upcoming = Sensor._upcoming_fixtures(fixtures, now)
        self.assertEqual([row["id"] for row in upcoming], ["m1", "m2"])
        self.assertEqual(upcoming[0]["fecha"], "2026-11-16")
        self.assertEqual(upcoming[0]["campo"], "Pabellón")
        self.assertIsNone(upcoming[1]["hora"])
        published = [
            {**base, "id": "seconds", "hora": "13:30:00"},
            {**base, "id": "utc", "hora": None, "fecha_hora_utc": "2026-11-16T14:15:00Z"},
        ]
        self.assertEqual([row["hora"] for row in Sensor._upcoming_fixtures(published, now)],
                         ["13:30", "15:15"])
        past = Sensor._upcoming_fixtures([
            {**base, "estado": "finished", "fecha": "2026-11-09",
             "marcador": {"local": 40, "visitante": 32}}], now, past=True)
        self.assertEqual(past[0]["marcador"], {"local": 40, "visitante": 32})

    def test_round_status_ignores_postponements_and_calendar_gaps(self):
        fixtures = [
            {"jornada": 1, "fecha": "2026-11-01", "estado": "finished"},
            {"jornada": 2, "fecha": "07/11/2026", "estado": "finished"},
            {"jornada": 2, "fecha": "2026-11-27", "estado": "postponed"},
            {"jornada": 3, "fecha": "14/11/2026", "estado": "scheduled"},
            {"jornada": 3, "fecha": "2026-11-15", "estado": "scheduled"},
            {"jornada": 4, "fecha": "fecha pendiente", "estado": "scheduled"},
        ]
        self.assertEqual(Sensor._round_status(fixtures, date(2026, 11, 11)), {
            "current": None, "last_completed": 1, "next": 3,
        })
        self.assertEqual(Sensor._round_status(fixtures, date(2026, 11, 15)), {
            "current": 3, "last_completed": 1, "next": None,
        })
        self.assertIsNone(Sensor._round_status(fixtures, date(2026, 11, 27))["current"])

    async def test_refresh_signal_schedules_entity_update(self):
        sensor = Sensor.FBMCompetitionsSensor(
            types.SimpleNamespace(), types.SimpleNamespace(entry_id="entry"))
        sensor.async_on_remove = lambda unsub: None
        called=[]
        sensor.async_schedule_update_ha_state = lambda force: called.append(force)
        original=Sensor.FBMCompetitionsSensor.__bases__
        try:
            # Fake SensorEntity has no lifecycle implementation.
            sensor.__class__.__bases__[0].async_added_to_hass = AsyncMock()
            await sensor.async_added_to_hass()
        finally:
            delattr(sensor.__class__.__bases__[0], "async_added_to_hass")
        self.assertEqual(registered[-1][0], "fbm_competitions_refresh_entry")
        registered[-1][1]()
        self.assertEqual(called, [True])

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
            archive.follow(identity, display={"team_name": "Team", "competition_name": "Alevín Plata"})
            fixture_day = datetime.now(Sensor.ZoneInfo("Europe/Madrid")).date().isoformat()
            crest = "data:image/png;base64,iVBORw0KGgo="
            archive.record(identity, "standings", {"clasificacion": [
                {"id": "team1", "equipo": "Team", "posicion": 1,
                 "ganados": 4, "perdidos": 0, "escudo": "PRIVATE_IMAGE"}]})
            archive.record(identity, "fixtures", {"partidos": [
                {"id": "game1", "local": "Team", "visitante": "Other",
                 "estado": "finished", "fecha": fixture_day,
                 "marcador": {"local": 45, "visitante": 38},
                 "direccion": "Pabellón municipal", "img_local": crest, "img_visitante": "PRIVATE_IMAGE"},
            ]})
            archive.record(identity, "roster", {"jugadores": [
                {"id": "player", "nombre": "PRIVATE_CHILD", "foto": "PRIVATE_IMAGE"}]},
                subject="team1")
            summary = Sensor._read_competition_summary(path)
            self.assertEqual(summary["count"], 1)
            self.assertEqual(summary["groups"][0]["teams"], 1)
            self.assertEqual(summary["groups"][0]["matches"], 1)
            self.assertEqual(summary["groups"][0]["competition_name"], "Alevín Plata")
            self.assertEqual(archive.latest(identity, "fixtures")["payload"]["escudos"], {"Team": crest})
            self.assertNotIn(crest, str(summary))
            self.assertNotIn("PRIVATE_CHILD", str(summary))
            self.assertNotIn("PRIVATE_IMAGE", str(summary))
            self.assertEqual(summary["groups"][0]["past_fixtures"][0]["direccion"], "Pabellón municipal")
            self.assertEqual(summary["groups"][0]["ranking"], [{
                "id": "team1", "equipo": "Team", "posicion": 1, "ganados": 4, "perdidos": 0
            }])
            self.assertEqual(summary["groups"][0]["recent_results"], [{
                "local": "Team", "visitante": "Other", "fecha": fixture_day,
                "marcador": {"local": 45, "visitante": 38},
            }])

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
