"""Regression tests for the offline MCP-facing FBM match preview."""
import unittest
import importlib.util
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "custom_components/fbm/competition_match_preview.py"
spec = importlib.util.spec_from_file_location("competition_match_preview", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
match_preview = mod.match_preview


class MatchPreviewTests(unittest.TestCase):
    def setUp(self):
        self.standings = {"clasificacion": [
            {"equipo": "PINTO", "posicion": 1, "ganados": 4},
            {"equipo": "PARLA", "posicion": 2, "ganados": 3},
        ]}
        self.fixtures = {"partidos": [
            {"fecha": "01/11/2026", "hora": "10:00:00", "local": "PINTO",
             "visitante": "PARLA", "jornada": 3, "estado": "finished",
             "marcador": {"local": 55, "visitante": 45}},
            {"fecha": "07/11/2026", "hora": "10:00:00", "local": "PARLA",
             "visitante": "OTHER", "estado": "finished",
             "marcador": {"local": 70, "visitante": 60}},
            {"fecha": "14/11/2026", "hora": "14:00:00", "local": "PARLA",
             "visitante": "PINTO", "jornada": 5, "estado": "scheduled",
             "campo": "LA CANTUEÑA", "direccion": "Parla", "marcador": None},
            {"fecha": "21/11/2026", "hora": "11:00:00", "local": "PINTO",
             "visitante": "OTHER", "estado": "scheduled", "marcador": None},
        ]}

    def test_next_match_form_previous_and_coverage(self):
        report = match_preview(self.standings, self.fixtures, "PINTO")
        self.assertEqual(report["rival"], "PARLA")
        self.assertEqual(report["proximo_partido"]["jornada"], 5)
        self.assertEqual(report["proximo_partido"]["campo"], "LA CANTUEÑA")
        self.assertEqual(len(report["ultimos_cuatro"]["PARLA"]), 2)
        self.assertEqual(len(report["enfrentamientos_previos"]), 1)
        self.assertEqual(report["cobertura"]["partidos_con_marcador"], 2)

    def test_missing_rival_is_not_invented(self):
        report = match_preview(self.standings, {"partidos": []}, "PINTO")
        self.assertIsNone(report["rival"])
        self.assertIsNone(report["proximo_partido"])

    def test_unknown_team_rejected(self):
        with self.assertRaises(ValueError):
            match_preview(self.standings, self.fixtures, "UNKNOWN")

    def test_bad_scores_do_not_count(self):
        fixture = {"partidos": [{"fecha": "01/11/2026", "local": "PINTO",
                                 "visitante": "PARLA", "estado": "finished",
                                 "marcador": {"local": None, "visitante": 10}}]}
        report = match_preview(self.standings, fixture, "PINTO")
        self.assertEqual(report["cobertura"]["partidos_con_marcador"], 0)


if __name__ == "__main__":
    unittest.main()
