"""APK JugadoresEquipoResponseDto synthetic responses; never request real player data."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components/fbm/team_roster.py"
spec = importlib.util.spec_from_file_location("team_roster", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RosterTests(unittest.TestCase):
    def test_apk_mis_jugadores_and_aggregates(self):
        response = {"error": "", "misJugadores": [
            {"id": "a", "nombre": "Jugador de prueba",
             "nombreEquipo": "Equipo de prueba", "temporada": "2026-27",
             "partidosJugados": 4, "puntosTotales": 20, "mediaPuntos": 5,
             "puntosPorPartido": 5.0, "minutosPorPartido": 12.5,
             "foto": "private-photo-url", "club": "other field"}
        ]}
        result = mod.normalize_team_roster(response)
        self.assertEqual(result["total"], 1)
        player = result["jugadores"][0]
        self.assertEqual(player["puntos_totales"], 20)
        self.assertEqual(player["puntos_por_partido"], 5.0)
        self.assertNotIn("foto", player)
        self.assertNotIn("club", player)
        self.assertNotIn("private-photo-url", str(result))

    def test_live_lowercase_roster_spelling(self):
        result = mod.normalize_team_roster({"error": "", "misjugadores": [
            {"id": "p1", "nombre": "Ejemplo"}
        ]})
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["jugadores"][0]["id"], "p1")
        with self.assertRaises(mod.PlayerRosterError):
            mod.normalize_team_roster({"error": "", "misjugadores": [],
                                       "misJugadores": []})

    def test_safe_diagnostic_only_reports_aggregate_types_and_errors(self):
        response={"error":"","misjugadores":[
            {"Id":"private","Nombre":"Private Name","PartidosJugados":3.0,
             "PuntosTotales":12,"MediaPuntos":4.0},
            {"Id":"private2","Nombre":"Private Name Two","PartidosJugados":2,
             "PuntosTotales":9,"MediaPuntos":3.5},
        ]}
        result=mod.diagnose_roster_rows(response)
        self.assertEqual(result["total"],2)
        self.assertEqual(result["validation_errors"],{"invalid_integer":1})
        self.assertEqual(result["numeric_types"]["PartidosJugados"],{"float":1,"int":1})
        for private in ("private", "Private Name", "private2"):
            self.assertNotIn(private,str(result))

    def test_minus_one_is_missing_not_negative_statistic(self):
        result = mod.normalize_team_roster({"error": "", "misjugadores": [
            {"Id": "id-1", "Nombre": "Prueba", "PartidosJugados": -1,
             "PuntosTotales": -1, "MediaPuntos": 0}
        ]})
        self.assertIsNone(result["jugadores"][0]["partidos_jugados"])
        self.assertIsNone(result["jugadores"][0]["puntos_totales"])
        with self.assertRaises(mod.PlayerRosterError):
            mod.normalize_team_roster({"error": "", "misjugadores": [
                {"Id": "id-2", "Nombre": "Prueba", "PartidosJugados": -2}
            ]})

    def test_live_pascalcase_roster_fields(self):
        response = {"error": "", "misjugadores": [
            {"Id": "official-id", "Nombre": "Jugador de prueba",
             "NombreEquipo": "Tercer Tiempo", "Temporada": "26/27",
             "PartidosJugados": 4, "PuntosTotales": 31,
             "MediaPuntos": 7.75, "PuntosPorPartido": 7.75,
             "MinutosPorPartido": 11.2, "Foto": "private-picture", "Club": "private"}]}
        result = mod.normalize_team_roster(response)
        self.assertEqual(result["total"], 1)
        player = result["jugadores"][0]
        self.assertEqual(player["id"], "official-id")
        self.assertEqual(player["nombre"], "Jugador de prueba")
        self.assertEqual(player["puntos_totales"], 31)
        self.assertEqual(player["media_puntos"], 7.75)
        self.assertEqual(player["minutos_por_partido"], 11.2)
        self.assertNotIn("Foto", player)
        self.assertNotIn("Club", player)

    def test_mixed_pascal_and_camelcase_rejected(self):
        with self.assertRaises(mod.PlayerRosterError):
            mod.normalize_team_roster({"error":"", "misjugadores":[
                {"Id":"one","Nombre":"Example","puntosTotales": 12}]})
        with self.assertRaises(mod.PlayerRosterError):
            mod.normalize_team_roster({"error":"", "misjugadores":[
                {"Id":"one","Nombre":"Example","MediaPuntos": True}]})

    def test_stats_missing_not_fabricated(self):
        result = mod.normalize_team_roster({"error": "", "misJugadores": [
            {"id": "b", "nombre": "Ejemplo"}
        ]})
        player = result["jugadores"][0]
        self.assertIsNone(player["partidos_jugados"])
        self.assertIsNone(player["puntos_totales"])
        self.assertIsNone(player["minutos_por_partido"])

    def test_absent_or_bad_roster_is_not_empty_success(self):
        for response in ({"error": ""}, {"error": "denied", "misJugadores": []},
                         {"error": "", "jugadores": []}, {"error": "", "misJugadores": None}):
            with self.subTest(response=response), self.assertRaises(mod.PlayerRosterError):
                mod.normalize_team_roster(response)

    def test_duplicate_or_malformed_player_rejected(self):
        cases = (
            [{"id": "a", "nombre": "A"}, {"id": "a", "nombre": "B"}],
            [{"id": "a", "nombre": "A", "partidosJugados": True}],
            [{"id": "a", "nombre": "A", "puntosPorPartido": float("nan")}],
            [{"id": "", "nombre": "A"}],
        )
        for rows in cases:
            with self.subTest(rows=str(rows)[:20]), self.assertRaises(mod.PlayerRosterError):
                mod.normalize_team_roster({"error": "", "misJugadores": rows})


if __name__ == "__main__":
    unittest.main()
