"""Normalizacion de horarios con respuestas simuladas y sin red."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'custom_components/fbm/team_schedule.py'
spec = importlib.util.spec_from_file_location('team_schedule_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


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

    def test_empty_and_invalid_responses(self):
        self.assertEqual(module.normalize_team_schedule({'error': '', 'jornadaActual': 0, 'partidos': []})['partidos'], [])
        for response in ({'error': 'failed', 'jornadaActual': 0, 'partidos': []},
                         {'error': '', 'jornadaActual': True, 'partidos': []},
                         {'error': '', 'jornadaActual': 1, 'partidos': [{}]}):
            with self.subTest(response=response), self.assertRaises(module.TeamScheduleError):
                module.normalize_team_schedule(response)
