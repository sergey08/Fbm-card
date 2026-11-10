"""Offline tests for FBM competition archive and group synchronization."""
import asyncio
from datetime import date
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

Archive = module("competition_archive").CompetitionArchive
sync_group = module("competition_sync").sync_group
preview_group = module("competition_sync").preview_group


def identity(verified=True):
    return {"season_id": "2026-27", "phase_id": "phase1",
            "group_id": "group1", "season_verified": verified}


class FakeClient:
    def __init__(self, verified=True):
        self.verified = verified
        self.calls = []

    async def async_team_group_identity(self, team):
        self.calls.append(("identity", team))
        return identity(self.verified)

    async def async_team_standings(self, team):
        self.calls.append(("standings", team))
        return {"clasificacion": [{"id": "a", "equipo": "A"},
                                  {"id": "b", "equipo": "B"}]}

    async def async_team_schedule(self, team, start, end):
        self.calls.append(("schedule", team))
        return {"partidos": [{"id": "m1", "local": "A", "visitante": "B"}]}

    async def async_team_roster(self, team):
        self.calls.append(("roster", team))
        return {"jugadores": [{"id": team + "-p1", "nombre": "Ejemplo",
                               "puntos_totales": 5, "foto": "private-photo"}]}


class CompetitionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Archive(str(Path(tmp.name) / "competition.sqlite"))

    def test_requires_verified_season(self):
        with self.assertRaises(ValueError):
            self.store.follow(identity(False))
        client = FakeClient(verified=False)
        result = asyncio.run(sync_group(client, self.store, "a",
                                       date(2026, 10, 1), date(2026, 11, 1)))
        self.assertEqual(result["status"], "season_unverified")
        self.assertEqual(client.calls, [("identity", "a")])
        self.assertEqual(self.store.followed(), [])

    def test_preview_reads_group_without_players_or_storage(self):
        client = FakeClient(verified=False)
        result = asyncio.run(preview_group(client, "a",
                                           date(2026, 10, 1), date(2026, 11, 1)))
        self.assertEqual(result["status"], "preview")
        self.assertFalse(result["persisted"])
        self.assertFalse(result["season_verified"])
        self.assertEqual(result["team_count"], 2)
        self.assertEqual(result["match_count"], 1)
        self.assertEqual(len(client.calls), 3)
        self.assertFalse(any(kind == "roster" for kind, _ in client.calls))
        self.assertEqual(self.store.followed(), [])

    def test_full_group_deduped_and_photos_removed(self):
        client = FakeClient()
        async def sync():
            return await sync_group(client, self.store, "a",
                                    date(2026, 10, 1), date(2026, 11, 1))
        report = asyncio.run(sync())
        self.assertEqual(report["team_count"], 2)
        self.assertEqual(report["rosters_saved"], 2)
        self.assertEqual(report["fixture_count"], 1)
        self.assertEqual(len(self.store.followed()), 1)
        saved = self.store.latest(identity(), "roster", "a")["payload"]
        self.assertEqual(saved["jugadores"][0]["puntos_totales"], 5)
        self.assertNotIn("foto", saved["jugadores"][0])
        self.assertNotIn("private-photo", str(saved))
        reopened = Archive(self.store.path)
        self.assertEqual(reopened.latest(identity(), "fixtures")["payload"]["partidos"][0]["id"], "m1")

    def test_stale_records_and_identity_separation(self):
        self.store.follow(identity())
        self.assertTrue(self.store.record(identity(), "standings", {"clasificacion": []},
                                          observed_at="2026-11-10T12:00:00Z"))
        self.assertFalse(self.store.record(identity(), "standings", {"clasificacion": []},
                                           observed_at="2026-11-09T12:00:00Z"))
        self.assertFalse(self.store.record(identity(), "standings", {"clasificacion": []},
                                           observed_at="2026-11-11T12:00:00Z"))  # sin cambios
        other = {**identity(), "group_id": "group2"}
        self.assertIsNone(self.store.latest(other, "standings"))
        with self.assertRaises(ValueError):
            self.store.record(identity(), "unknown", {})
        self.store.unfollow(identity())
        self.assertFalse(self.store.record(identity(), "fixtures", {"partidos": []}))

    def test_reject_oversized_or_invalid_inputs(self):
        self.store.follow(identity())
        with self.assertRaises(ValueError):
            self.store.record(identity(), "roster", {"jugadores": []}, subject="")
        with self.assertRaises(ValueError):
            self.store.record(identity(), "standings", {"clasificacion": "not a list"})
        with self.assertRaises(ValueError):
            self.store.record(identity(), "roster", {"jugadores": [
                {"nombre": "x" * 2000000}]}, subject="a")


if __name__ == "__main__":
    unittest.main()
