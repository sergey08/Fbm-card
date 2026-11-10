"""Synthetic offline FBM opponent analytics tests."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "custom_components/fbm/competition_analysis.py"
spec = importlib.util.spec_from_file_location("competition_analysis", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.standings = {"clasificacion": [
            {"id": "a", "equipo": "Pinto", "posicion": 1,
             "jugados": 2, "ganados": 2, "perdidos": 0, "puntos": 4},
            {"id": "b", "equipo": "Rival", "posicion": 2,
             "jugados": 2, "ganados": 0, "perdidos": 2, "puntos": 2},
        ]}

    def test_official_fixtures_scores_and_player_totals(self):
        fixtures = {"partidos": [
            {"id": "m1", "local": "Pinto", "visitante": "Rival",
             "estado": "finished", "marcador": {"local": 50, "visitante": 40}},
            {"id": "m2", "local": "Rival", "visitante": "Pinto",
             "estado": "scheduled", "marcador": None},
            {"id": "m1", "local": "Pinto", "visitante": "Rival",
             "estado": "finished", "marcador": {"local": 50, "visitante": 40}},
        ]}
        rosters = {"a": {"jugadores": [{"id": "a1", "nombre": "Jugador A",
                                        "puntos_totales": 36, "foto": "PRIVATE"}]},
                   "b": {"jugadores": [{"id": "b1", "nombre": "Jugador B",
                                        "puntos_totales": None}]}}
        result = mod.competition_analysis(self.standings, fixtures, rosters)
        self.assertEqual(result["numero_equipos"], 2)
        self.assertEqual(result["partidos_con_marcador"], 1)
        self.assertEqual(result["equipos"][0]["media_favor"], 50)
        self.assertEqual(result["equipos"][1]["media_contra"], 50)
        self.assertEqual(len(result["anotadores"]), 1)
        self.assertEqual(result["anotadores"][0]["puntos_totales"], 36)
        self.assertNotIn("PRIVATE", str(result))

    def test_missing_or_ambiguous_official_scores_are_not_guessed(self):
        fixtures = {"partidos": [
            {"id": "m1", "local": "Pinto", "visitante": "Rival", "estado": "unknown",
             "marcador": {"local": 30, "visitante": 20}},
            {"id": "m2", "local": "Pinto", "visitante": "Rival", "estado": "finished",
             "marcador": {"local": "30", "visitante": "20"}},
        ]}
        result = mod.competition_analysis(self.standings, fixtures)
        self.assertEqual(result["partidos_con_marcador"], 0)
        self.assertIsNone(result["equipos"][0]["media_favor"])
        self.assertEqual(result["anotadores"], [])

    def test_duplicate_team_ids_rejected(self):
        standings = {"clasificacion": [
            {"id": "a", "equipo": "Pinto"}, {"id": "a", "equipo": "Other"}]}
        with self.assertRaises(ValueError):
            mod.competition_analysis(standings, {"partidos": []})


if __name__ == "__main__":
    unittest.main()
