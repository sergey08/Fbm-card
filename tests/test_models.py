"""Pruebas del contrato FBM: sin red ni datos deportivos inventados."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fbm/models.py"
spec = importlib.util.spec_from_file_location("fbm_models_isolated", PATH)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)

SOURCE = "https://appaficionfbm.gesdeportiva.es/v2/equipo.ashx"
WHEN = "2026-11-08T15:00:00+00:00"
TEAMS = {"local": "Equipo local", "visitante": "Equipo visitante"}


class ModelTests(unittest.TestCase):
    def test_official_hosts(self):
        for url in ("https://fbm.es/", "https://www.fbm.es/competiciones",
                    "https://appaficionfbm.gesdeportiva.es/v2/equipo.ashx"):
            self.assertEqual(models.validate_official_url(url), url)

    def test_reject_host_spoofing_and_http(self):
        for url in ("http://fbm.es/", "https://fbm.es.ejemplo.com/",
                    "https://ejemplo.com/fbm.es", "https://fbm.es@ejemplo.com/",
                    "https://fbm.es:8080/", "https://user:pass@fbm.es/"):
            with self.subTest(url=url), self.assertRaises(models.FBMDataError):
                models.validate_official_url(url)

    def test_unknown_is_not_inferred_live(self):
        data = models.normalize_match(TEAMS, source_url=SOURCE, fetched_at=WHEN)
        self.assertEqual(data["state"], "unknown")
        self.assertIsNone(data["score"])
        self.assertIsNone(data["period"])

    def test_live_requires_explicit_state(self):
        data = models.normalize_match(
            {**TEAMS, "state": "live", "period": 2,
             "score": {"local": 20, "visitante": 18}},
            source_url=SOURCE, fetched_at=WHEN,
        )
        self.assertEqual(data["state"], "live")
        self.assertEqual(data["period"], 2)

    def test_reject_bad_score(self):
        for score in ({"local": 12}, {"local": -1, "visitante": 0},
                      {"local": True, "visitante": 0}):
            with self.subTest(score=score), self.assertRaises(models.FBMDataError):
                models.normalize_match(
                    {**TEAMS, "score": score}, source_url=SOURCE, fetched_at=WHEN
                )

    def test_reject_unknown_state(self):
        with self.assertRaises(models.FBMDataError):
            models.normalize_match(
                {**TEAMS, "state": "probably_live"},
                source_url=SOURCE, fetched_at=WHEN,
            )

    def test_reject_missing_teams_and_time(self):
        with self.assertRaises(models.FBMDataError):
            models.normalize_match({"local": "A"}, source_url=SOURCE, fetched_at=WHEN)
        with self.assertRaises(models.FBMDataError):
            models.normalize_match(TEAMS, source_url=SOURCE, fetched_at="ayer")


if __name__ == "__main__":
    unittest.main()
