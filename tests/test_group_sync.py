"""Isolated coordinator tests; synthetic data, no FBM traffic or HA writes."""
import asyncio
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

FollowedGroups = load("followed_groups_store").FollowedGroups
GroupSyncCoordinator = load("group_sync").GroupSyncCoordinator


class GroupSyncTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FollowedGroups(str(Path(self.tmp.name) / "fbm.sqlite"))
        self.calls = []
        async def fetch(season, group):
            self.calls.append((season, group))
            return {"clasificacion": [{"id": "a", "equipo": "Equipo A"}]}
        self.sync = GroupSyncCoordinator(self.store, fetch)
        self.monday = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)

    async def test_no_implicit_follow_or_request(self):
        self.assertEqual(await self.sync.refresh_due(now=self.monday), [])
        status = await self.sync.refresh("26", "g1", now=self.monday, manual=True)
        self.assertEqual(status["status"], "not_followed")
        self.assertEqual(self.calls, [])

    async def test_manual_and_weekday_interval(self):
        self.store.follow("26", "g1")
        first = await self.sync.refresh("26", "g1", now=self.monday)
        self.assertEqual(first["status"], "ok")
        self.assertTrue(first["classification_available"])
        self.assertEqual(first["source_status"]["jugadores"], "unverified")
        self.assertFalse(self.sync.due("26", "g1", now=datetime(2026,11,9,12,0,tzinfo=timezone.utc)))
        self.assertTrue(self.sync.due("26", "g1", now=datetime(2026,11,9,13,0,tzinfo=timezone.utc)))
        self.assertEqual(len(self.calls), 1)

    async def test_unfollow_preserves_snapshot(self):
        self.store.follow("26", "g1")
        await self.sync.refresh("26", "g1", now=self.monday)
        self.store.unfollow("26", "g1")
        self.assertFalse(self.sync.due("26", "g1", now=self.monday))
        state = await self.sync.refresh("26", "g1", now=self.monday, manual=True)
        self.assertEqual(state["status"], "not_followed")
        self.assertTrue(state["classification_available"])
        self.assertEqual(len(self.calls), 1)

    async def test_failure_keeps_previous_snapshot_and_redacts_exception(self):
        self.store.follow("26", "g1")
        await self.sync.refresh("26", "g1", now=self.monday)
        async def broken(*args):
            raise RuntimeError("secret-token-in-error")
        self.sync.fetch = broken
        result = await self.sync.refresh("26", "g1", now=self.monday, manual=True)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["classification_available"])
        self.assertNotIn("secret-token", str(result))

    async def test_weekend_interval_and_manual_override(self):
        self.store.follow("26", "g1")
        saturday = datetime(2026,11,14,10,0,tzinfo=timezone.utc)
        await self.sync.refresh("26", "g1", now=saturday)
        self.assertFalse(self.sync.due("26", "g1", now=datetime(2026,11,14,10,20,tzinfo=timezone.utc)))
        self.assertTrue(self.sync.due("26", "g1", now=datetime(2026,11,14,10,30,tzinfo=timezone.utc)))
        await self.sync.refresh("26", "g1", now=datetime(2026,11,14,10,20,tzinfo=timezone.utc), manual=True)
        self.assertEqual(len(self.calls), 2)

    async def test_recheck_unfollow_during_network(self):
        self.store.follow("26", "g1")
        async def fetch_then_unfollow(*args):
            self.store.unfollow("26", "g1")
            return {"clasificacion": []}
        self.sync.fetch = fetch_then_unfollow
        result = await self.sync.refresh("26", "g1", now=self.monday)
        self.assertEqual(result["status"], "not_followed")
        self.assertIsNone(self.store.latest("26", "g1"))

    def test_reject_invalid_intervals(self):
        with self.assertRaises(ValueError):
            GroupSyncCoordinator(self.store, lambda *a: None, weekday_minutes=0)

if __name__ == "__main__":
    unittest.main()
