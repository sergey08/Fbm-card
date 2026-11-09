"""Per-player match-stat APK DTO tests. Synthetic and offline."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "custom_components/fbm/match_player_stats.py"
spec = importlib.util.spec_from_file_location("match_player_stats", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MatchStatsTests(unittest.TestCase):
    def test_points_fouls_rebounds_and_assists(self):
        result = mod.normalize_match_player_stats({
            "nombre": "Jugador prueba", "componente_id": "opaque",
            "dorsal": "8", "puntos": 17, "faltascometidas": 3,
            "faltasrecibidas": 2, "rebotes": 7, "asistencias": 4,
            "valoracion": -2, "foto": "private-image", "otra": "private-data"
        })
        self.assertEqual(result["puntos"], 17)
        self.assertEqual(result["faltas_cometidas"], 3)
        self.assertEqual(result["faltas_recibidas"], 2)
        self.assertEqual(result["rebotes"], 7)
        self.assertEqual(result["asistencias"], 4)
        self.assertEqual(result["valoracion"], -2)
        self.assertNotIn("private-image", str(result))

    def test_missing_stats_are_unknown(self):
        result = mod.normalize_match_player_stats({"nombre": "Ejemplo"})
        self.assertIsNone(result["puntos"])
        self.assertIsNone(result["faltas_cometidas"])

    def test_reject_bad_stats_and_missing_name(self):
        for item in ({"nombre": ""}, {"nombre": "A", "puntos": True},
                     {"nombre": "A", "faltascometidas": -1},
                     {"nombre": "A", "rebotes": "5"}):
            with self.subTest(item=item), self.assertRaises(mod.MatchPlayerStatsError):
                mod.normalize_match_player_stats(item)


if __name__ == "__main__":
    unittest.main()
