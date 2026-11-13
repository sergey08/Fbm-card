"""Offline regression tests for read-only coverage metrics."""
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "custom_components/fbm/competition_coverage.py"
spec = importlib.util.spec_from_file_location("fbm_coverage_test", MODULE)
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class CoverageTests(unittest.TestCase):
    def test_missing_database_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "absent.db")
            self.assertEqual(coverage.read_coverage(path)["totals"]["teams"], 0)
            self.assertFalse(Path(path).exists())

    def test_followed_only_and_unique_games(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "coverage.db")
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE competitions (season TEXT, phase TEXT, group_id TEXT, followed INTEGER)")
                db.execute("CREATE TABLE snapshots (season TEXT, phase TEXT, group_id TEXT, source TEXT, subject TEXT, observed_at TEXT, payload TEXT)")
                db.executemany("INSERT INTO competitions VALUES (?,?,?,?)",
                               [("26/27", "p", "followed", 1), ("26/27", "p", "hidden", 0)])
                def insert(group, source, subject, payload):
                    db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)",
                               ("26/27", "p", group, source, subject, "2026-11-14T00:00:00Z", json.dumps(payload)))
                insert("followed", "standings", "", {"clasificacion": [{"id": "team"}]})
                insert("followed", "roster", "team", {"jugadores": [
                    {"id": "complete", "partidos_jugados": 1},
                    {"id": "duplicate", "partidos_jugados": 2},
                    {"id": "pending", "partidos_jugados": 1},
                    {"id": "unplayed", "partidos_jugados": 0}]})
                insert("followed", "player_stats", "complete", {"partidos": [{"id_partido": "m1", "puntos": 0}]})
                insert("followed", "player_stats", "duplicate", {"partidos": [
                    {"id_partido": "m1", "puntos": 5}, {"id_partido": "m1", "puntos": 5}]})
                insert("hidden", "standings", "", {"clasificacion": [{"id": "other"}]})
            result = coverage.read_coverage(path)
            self.assertEqual(len(result["groups"]), 1)
            self.assertEqual(result["totals"], {"teams": 1, "rosters": 1,
                                                  "players": 3, "complete": 1, "pending": 2})


if __name__ == "__main__":
    unittest.main()
