"""Pruebas de historial FBM sin conexión a servicios externos."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fbm/history.py"
spec = importlib.util.spec_from_file_location("fbm_history_isolated", PATH)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)

BASE = {
    "local": "A", "visitante": "B", "state": "live",
    "score": {"local": 10, "visitante": 8},
    "source_url": "https://fbm.es/", "fetched_at": "2026-11-08T15:00:00+00:00"
}


class HistoryTests(unittest.TestCase):
    def test_repeated_poll_does_not_add_revision(self):
        store = history.FBMHistory()
        self.assertTrue(store.record("official-1", BASE))
        self.assertFalse(store.record("official-1", {**BASE, "fetched_at": "2026-11-08T15:01:00+00:00"}))
        self.assertEqual(store.summary(), {"matches": 1, "revisions": 1})

    def test_score_change_adds_revision(self):
        store = history.FBMHistory()
        store.record("official-1", BASE)
        changed = {**BASE, "score": {"local": 12, "visitante": 8}, "fetched_at": "2026-11-08T15:02:00+00:00"}
        self.assertTrue(store.record("official-1", changed))
        self.assertEqual(len(store.revisions("official-1")), 2)

    def test_old_updates_ignored(self):
        store = history.FBMHistory()
        store.record("official-1", BASE)
        self.assertFalse(store.record("official-1", {**BASE, "fetched_at": "2026-11-08T14:00:00+00:00", "state": "finished"}))

    def test_capacity_and_copy_safety(self):
        store = history.FBMHistory(max_matches=1, max_revisions=1)
        store.record("one", BASE)
        item = store.latest("one")
        item["score"]["local"] = 999
        self.assertEqual(store.latest("one")["score"]["local"], 10)
        store.record("two", BASE)
        self.assertIsNone(store.latest("one"))

    def test_invalid_ids_and_timestamps(self):
        store = history.FBMHistory()
        with self.assertRaises(ValueError):
            store.record("", BASE)
        with self.assertRaises(ValueError):
            store.record("one", {**BASE, "fetched_at": "2026-11-08T15:00:00"})


if __name__ == "__main__":
    unittest.main()
