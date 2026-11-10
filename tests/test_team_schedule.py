"""Normalizacion de horarios con respuestas simuladas y sin red."""
import importlib.util
from pathlib import Path
import unittest

import sys
import types

root = Path(__file__).resolve().parents[1] / "custom_components/fbm"
pkg = types.ModuleType("fbm_image_test_schedule")
pkg.__path__ = [str(root)]
sys.modules[pkg.__name__] = pkg
for name in ("image_references", "team_schedule"):
    spec = importlib.util.spec_from_file_location(pkg.__name__ + "." + name, root / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
module = sys.modules[pkg.__name__ + ".team_schedule"]


class TeamScheduleTests(unittest.TestCase):
    def test_returns_matches_without_inventing_score_or_state(self):
        data = {'error': '', 'jornadaActual': 4, 'partidos': [
            {'IdPartido': 'opaque', 'NombreEquipoLocal': 'Alfa', 'NombreEquipoVisitante': 'Beta',
             'Fecha': 'fecha', 'Hora': 'hora', 'Estado': 'X', 'NumeroJornada': 5,
             'Resultados': {'unexpected': 'not-yet-understood'}}]}
        result = module.normalize_team_schedule(data)
        self.assertEqual(result['jornada_actual'], 4)
        self.assertEqual(result['partidos'][0]['local'], 'Alfa')
        self.assertEqual(result['partidos'][0]['estado_oficial'], 'X')
        self.assertEqual(result['partidos'][0]['estado'], 'unknown')
        self.assertIsNone(result['partidos'][0]['marcador'])
        self.assertNotIn('Resultados', result['partidos'][0])

    def test_only_finished_matches_with_two_numeric_scores_get_a_score(self):
        base = {'IdPartido': 'id', 'NombreEquipoLocal': 'Alfa', 'NombreEquipoVisitante': 'Beta'}
        matches = [
            {**base, 'Estado': 'Terminado', 'Resultados': {'ResultadoLocal': '32', 'ResultadoVisitante': '57'}},
            {**base, 'Estado': 'No comenzado', 'Resultados': {'ResultadoLocal': '-', 'ResultadoVisitante': '-'}},
            {**base, 'Estado': 'No comenzado', 'Resultados': {'ResultadoLocal': '0', 'ResultadoVisitante': '0'}},
            {**base, 'Estado': 'Terminado', 'Resultados': {'ResultadoLocal': '32', 'ResultadoVisitante': '-'}},
            {**base, 'Estado': 'Desconocido', 'Resultados': {'ResultadoLocal': '32', 'ResultadoVisitante': '57'}},
        ]
        result = module.normalize_team_schedule({'error': '', 'jornadaActual': 4, 'partidos': matches})['partidos']
        self.assertEqual(result[0]['marcador'], {'local': 32, 'visitante': 57})
        self.assertEqual(result[0]['estado'], 'finished')
        self.assertEqual(result[1]['estado'], 'scheduled')
        self.assertTrue(all(match['marcador'] is None for match in result[1:]))

    def test_embedded_team_logos_only_when_valid_images(self):
        import base64
        png = base64.b64encode(bytes([137,80,78,71,13,10,26,10])+b"crest").decode()
        match={"IdPartido":"m1","NombreEquipoLocal":"A","NombreEquipoVisitante":"B",
               "ImgEquipoLocal":png,"ImgEquipoVisitante":"not-an-image"}
        result=module.normalize_team_schedule({"error":"","jornadaActual":1,"partidos":[match]})
        game=result["partidos"][0]
        self.assertEqual(game["img_local"],"data:image/png;base64,"+png)
        self.assertNotIn("img_visitante",game)

    def test_real_apk_camelcase_dto_fields(self):
        # Names and types from EquipoPartidoDto and ResultadosDto in APK 5.0.42.
        payload = {"error": "", "jornadaActual": 7, "partidos": [
            {"idPartido": "match1", "nombreEquipoLocal": "Local",
             "nombreEquipoVisitante": "Visitante", "numeroJornada": 8,
             "fecha": "2026-11-14", "hora": "10:30", "estado": "Terminado",
             "resultados": {"resultadoLocal": "32", "resultadoVisitante": "27"}}
        ]}
        result = module.normalize_team_schedule(payload)
        self.assertEqual(result["jornada_actual"], 7)
        self.assertEqual(result["partidos"][0]["id"], "match1")
        self.assertEqual(result["partidos"][0]["jornada"], 8)
        self.assertEqual(result["partidos"][0]["marcador"], {"local": 32, "visitante": 27})
        self.assertEqual(result["partidos"][0]["estado"], "finished")

    def test_camelcase_unknown_state_never_invents_result(self):
        payload = {"error": "", "jornadaActual": 0, "partidos": [
            {"idPartido": "m", "nombreEquipoLocal": "A", "nombreEquipoVisitante": "B",
             "estado": "No confirmado", "resultados": {"resultadoLocal": "15",
                                                      "resultadoVisitante": "14"}}
        ]}
        match = module.normalize_team_schedule(payload)["partidos"][0]
        self.assertEqual(match["estado"], "unknown")
        self.assertIsNone(match["marcador"])

    def test_rejects_mixed_casing_without_complete_variant(self):
        payload = {"error": "", "jornadaActual": 2, "partidos": [
            {"idPartido": "m", "NombreEquipoLocal": "A", "nombreEquipoVisitante": "B"}
        ]}
        with self.assertRaises(module.TeamScheduleError):
            module.normalize_team_schedule(payload)

    def test_category_dto_has_no_current_matchday(self):
        response = {"error": "", "partidos": [{
            "idPartido": "id", "nombreEquipoLocal": "Local",
            "nombreEquipoVisitante": "Visitante", "estado": "No comenzado",
            "numeroJornada": 5}]}
        parsed = module.normalize_category_schedule(response)
        self.assertIsNone(parsed["jornada_actual"])
        self.assertEqual(parsed["partidos"][0]["jornada"], 5)
        self.assertEqual(parsed["partidos"][0]["estado"], "scheduled")

    def test_category_dto_does_not_require_team_jornada_actual(self):
        self.assertEqual(module.normalize_category_schedule(
            {"error": "", "partidos": []}),
            {"jornada_actual": None, "partidos": []})
        with self.assertRaises(module.TeamScheduleError):
            module.normalize_team_schedule({"error": "", "partidos": []})
        for invalid in ({"error": ""}, {"error": "bad", "partidos": []},
                        {"error": "", "partidos": "bad"}):
            with self.subTest(invalid=invalid), self.assertRaises(module.TeamScheduleError):
                module.normalize_category_schedule(invalid)

    def test_empty_and_invalid_responses(self):
        self.assertEqual(module.normalize_team_schedule({'error': '', 'jornadaActual': 0, 'partidos': []})['partidos'], [])
        for response in ({'error': 'failed', 'jornadaActual': 0, 'partidos': []},
                         {'error': '', 'jornadaActual': True, 'partidos': []},
                         {'error': '', 'jornadaActual': 1, 'partidos': [{}]}):
            with self.subTest(response=response), self.assertRaises(module.TeamScheduleError):
                module.normalize_team_schedule(response)
