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
        self.assertNotIn('score', result['partidos'][0])
        self.assertNotIn('Resultados', result['partidos'][0])

    def test_empty_and_invalid_responses(self):
        self.assertEqual(module.normalize_team_schedule({'error': '', 'jornadaActual': 0, 'partidos': []})['partidos'], [])
        for response in ({'error': 'failed', 'jornadaActual': 0, 'partidos': []},
                         {'error': '', 'jornadaActual': True, 'partidos': []},
                         {'error': '', 'jornadaActual': 1, 'partidos': [{}]}):
            with self.subTest(response=response), self.assertRaises(module.TeamScheduleError):
                module.normalize_team_schedule(response)
