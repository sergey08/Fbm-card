"""Offline synthetic APK contracts; no real athlete data or requests."""
import importlib.util
from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1] / "custom_components/fbm"

def load(name):
    spec = importlib.util.spec_from_file_location(name, root / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

protocol = load("player_protocol")
stats = load("player_statistics")


class PlayerStatsTests(unittest.TestCase):
    def test_post_forms_match_apk_method_literals(self):
        for action in ("datosGlobalesJugadorEquipo", "datosMediasJugadorPartidos"):
            data = protocol.player_stats_fields("device", "key", "p", "t", "component", "season", action=action)
            self.assertEqual(data, {"accion": action, "id_dispositivo": "device", "key": "key",
                "id_jugador": "p", "id_equipo": "t", "id_componente_club": "component",
                "id_temporada": "season"})
        with self.assertRaises(ValueError):
            protocol.player_stats_fields("d", "k", "p", "t", "", "s", action="datosGlobalesJugadorEquipo")
        with self.assertRaises(ValueError):
            protocol.player_stats_fields("d", "k", "p", "t", "c", "s", action="registrar")

    def test_global_fields_and_availability_are_explicit(self):
        result = stats.normalize_global_player_stats({"error": "", "puntosTotalesJugador": 35,
            "puntosMediaJugador": 7.5, "faltasCometidasTotalesJugador": 2,
            "mostrarDatosEstadisticosAmpliados": False, "key": "secret"})
        self.assertEqual(result["estadisticas"]["puntos_totales"], 35)
        self.assertEqual(result["estadisticas"]["media_puntos"], 7.5)
        self.assertEqual(result["estadisticas"]["faltas_cometidas"], 2)
        self.assertIsNone(result["estadisticas"]["rebotes"])
        self.assertFalse(result["ampliadas_disponibles"])
        self.assertNotIn("secret", str(result))

    def test_match_list_converts_numeric_strings_and_preserves_unavailable(self):
        result = stats.normalize_player_match_list({"error": "", "listaDatosPartido": [
            {"idPartido": "m1", "nombreEquipoRival": "Rival",
             "puntos": "12", "faltaCometida": "3", "rebotesTotal": "",
             "valoracion": "-2", "local": True, "foto": "not-exported"}]})
        row = result["partidos"][0]
        self.assertEqual(row["puntos"], 12)
        self.assertEqual(row["faltas_cometidas"], 3)
        self.assertIsNone(row["rebotes"])
        self.assertEqual(row["valoracion"], -2)
        self.assertNotIn("not-exported", str(result))

    def test_live_pascalcase_match_stats(self):
        result=stats.normalize_player_match_list({"error":"","listaDatosPartido":[
            {"IdPartido":"m1","FechaPartido":"2026-11-05",
             "NombreEquipoRival":"Rival de ejemplo","Local":False,
             "Puntos":11,"Asistencia":"2","FaltaCometida":3,
             "FaltaRecibida":"","RebotesTotal":"7",
             "RebotesDefensivos":"4","RebotesOfensivos":"3",
             "Recuperaciones":"","Perdidas":"1","Valoracion":-2}
        ]})
        record=result["partidos"][0]
        self.assertEqual(result["total"],1)
        self.assertEqual(record["puntos"],11)
        self.assertEqual(record["asistencias"],2)
        self.assertEqual(record["faltas_cometidas"],3)
        self.assertIsNone(record["faltas_recibidas"])
        self.assertEqual(record["rebotes"],7)
        self.assertEqual(record["valoracion"],-2)

    def test_reject_mixed_match_casing(self):
        with self.assertRaises(stats.PlayerStatisticsError):
            stats.normalize_player_match_list({"error":"","listaDatosPartido":[
                {"IdPartido":"m1","Puntos":4,"puntos":99}]})

    def test_fail_closed_for_missing_error_duplicates_and_non_numeric(self):
        invalid = [
            {"error": "private", "listaDatosPartido": []},
            {"error": "", "listaDatosPartido": [{"idPartido": "m"}, {"idPartido": "m"}]},
            {"error": "", "listaDatosPartido": [{"idPartido": "m", "puntos": "unknown"}]},
            {"error": "", "listaDatosPartido": None},
        ]
        for value in invalid:
            with self.subTest(value=str(value)[:30]), self.assertRaises(stats.PlayerStatisticsError):
                stats.normalize_player_match_list(value)
        with self.assertRaises(stats.PlayerStatisticsError):
            stats.normalize_global_player_stats({"error": "", "puntosTotalesJugador": True})


if __name__ == "__main__":
    unittest.main()
