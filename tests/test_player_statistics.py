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

    def test_non_numeric_text_patterns_are_aggregated_without_values(self):
        response={"error":"","listaDatosPartido":[
            {"IdPartido":"id-1","Asistencia":"—","RebotesTotal":"N/D","Perdidas":"  "},
            {"IdPartido":"id-2","Asistencia":"0,5","RebotesTotal":"dato interno"}
        ]}
        shape=stats.diagnose_match_rows(response)
        self.assertEqual(shape["statistic_types"]["Asistencia"]["text_patterns"]["dash_placeholder"],1)
        self.assertEqual(shape["statistic_types"]["Asistencia"]["text_patterns"]["decimal_separator"],1)
        self.assertEqual(shape["statistic_types"]["RebotesTotal"]["text_patterns"]["unavailable_label"],1)
        for private in ("id-1","id-2","dato interno","N/D","0,5"):
            self.assertNotIn(private,str(shape))

    def test_private_safe_aggregate_match_diagnostics(self):
        response={"error":"","listaDatosPartido":[
            {"IdPartido":"private1","NombreEquipoRival":"Private Rival",
             "Puntos":-1,"Asistencia":"--"},
            {"IdPartido":"private2","Puntos":4,"Asistencia":"--"},
            {"IdPartido":"private2","Puntos":4},
        ]}
        result=stats.diagnose_match_rows(response)
        self.assertEqual(result["total"],3)
        self.assertEqual(result["errors"]["duplicate_across_rows"],1)
        self.assertEqual(result["errors"]["negative_statistic"],1)
        self.assertEqual(result["errors"]["non_numeric_statistic"],1)
        self.assertEqual(result["statistic_types"]["Puntos"]["negative_count"],1)
        for value in ("private1","private2","Private Rival","--"):
            self.assertNotIn(value,str(result))

    def test_official_dashes_are_missing_not_zero(self):
        response={"error":"","listaDatosPartido":[
            {"IdPartido":"match-1","Puntos":12,"FaltaCometida":2,
             "Asistencia":"-","FaltaRecibida":"--",
             "RebotesTotal":"—","RebotesDefensivos":"–",
             "Recuperaciones":"-","Perdidas":"-","Valoracion":-3}
        ]}
        parsed=stats.normalize_player_match_list(response)["partidos"][0]
        self.assertEqual(parsed["puntos"],12)
        self.assertEqual(parsed["faltas_cometidas"],2)
        self.assertEqual(parsed["valoracion"],-3)
        for key in ("asistencias","faltas_recibidas","rebotes",
                    "rebotes_defensivos","recuperaciones","perdidas"):
            self.assertIsNone(parsed[key])
        with self.assertRaises(stats.PlayerStatisticsError):
            stats.normalize_player_match_list({"error":"","listaDatosPartido":[
                {"IdPartido":"match-2","Asistencia":"unknown"}]})

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
