"""Pure storage tests: no FBM traffic, HA changes or identity access."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fbm/followed_groups_store.py"
spec = importlib.util.spec_from_file_location("followed_groups_store", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FollowedGroups = module.FollowedGroups

class FollowedGroupsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = FollowedGroups(str(Path(self.temp.name) / "fbm.sqlite"))
        self.payload = {"clasificacion": [{"id": "eq1", "equipo": "Equipo A"}]}
        self.t1 = "2026-11-09T10:00:00+00:00"
        self.t0 = "2026-11-08T10:00:00+00:00"

    def test_explicit_follow_only(self):
        self.assertEqual(self.store.followed(), [])
        self.assertFalse(self.store.record("2026", "g1", "clasificacion",
                                           self.payload, observed_at=self.t1))
        self.store.follow("2026", "g1")
        self.store.follow("2026", "g1")
        self.assertEqual(self.store.followed(), [("2026", "g1")])

    def test_unfollow_preserves_history_and_blocks_updates(self):
        self.store.follow("2026", "g1")
        self.assertTrue(self.store.record("2026", "g1", "clasificacion",
                                          self.payload, observed_at=self.t1))
        self.store.unfollow("2026", "g1")
        self.assertEqual(self.store.followed(), [])
        self.assertFalse(self.store.record("2026", "g1", "clasificacion",
                                           self.payload, observed_at="2026-11-10T10:00:00Z"))
        self.assertFalse(self.store.latest("2026", "g1")["followed"])

    def test_group_isolation_and_persistence(self):
        self.store.follow("2026", "g1")
        self.store.follow("2026", "g2")
        self.store.record("2026", "g1", "clasificacion", self.payload,
                          observed_at=self.t1)
        self.assertIsNone(self.store.latest("2026", "g2"))
        reopened = FollowedGroups(self.store.path)
        self.assertEqual(reopened.latest("2026", "g1")["payload"], self.payload)

    def test_error_old_response_and_unverified_source(self):
        self.store.follow("2026", "g1")
        self.store.record("2026", "g1", "clasificacion", self.payload,
                          observed_at=self.t1)
        with self.assertRaises(ValueError):
            self.store.record("2026", "g1", "clasificacion", {"error": "fallo"})
        with self.assertRaises(ValueError):
            self.store.record("2026", "g1", "jugadores", self.payload)
        self.assertFalse(self.store.record("2026", "g1", "clasificacion",
                                           {"clasificacion": []}, observed_at=self.t0))
        self.assertEqual(self.store.latest("2026", "g1")["payload"], self.payload)

if __name__ == "__main__":
    unittest.main()
