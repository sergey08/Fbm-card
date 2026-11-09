"""Clasificacion sin red, con valores simulados."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'custom_components/fbm/team_standings.py'
spec = importlib.util.spec_from_file_location('team_standings_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TeamStandingsTests(unittest.TestCase):
    def test_preserves_order_and_values_without_recalculation(self):
        rows = [
            {'IdEquipo': 'opaque-b', 'NombreEquipo': 'B', 'Posicion': 2, 'PartidosJugados': 3, 'PartidosGanados': 1, 'PartidosPerdidos': 2, 'Puntos': 4},
            {'IdEquipo': 'opaque-a', 'NombreEquipo': 'A', 'Posicion': 1, 'PartidosJugados': 3, 'PartidosGanados': 3, 'PartidosPerdidos': 0, 'Puntos': 6},
        ]
        result = module.normalize_standings({'error': '', 'clasificacion': rows})
        self.assertEqual([r['equipo'] for r in result['clasificacion']], ['B', 'A'])
        self.assertEqual(result['clasificacion'][0], {'id': 'opaque-b', 'equipo': 'B', 'posicion': 2,
                         'jugados': 3, 'ganados': 1, 'perdidos': 2, 'puntos': 4})

    def test_empty_and_malformed_responses(self):
        self.assertEqual(module.normalize_standings({'error': '', 'clasificacion': []}), {'clasificacion': []})
        invalid = ({'error': 'error', 'clasificacion': []}, {'clasificacion': []},
                   {'error': '', 'clasificacion': {}}, {'error': '', 'clasificacion': [{}]},
                   {'error': '', 'clasificacion': [{'IdEquipo': 'i', 'NombreEquipo': 'A', 'Posicion': True}]})
        for response in invalid:
            with self.subTest(response=response), self.assertRaises(module.TeamStandingsError):
                module.normalize_standings(response)
