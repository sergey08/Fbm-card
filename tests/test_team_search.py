"""Normalizacion de busquedas, con respuestas simuladas y sin red."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'custom_components/fbm/team_search.py'
spec = importlib.util.spec_from_file_location('team_search_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TeamSearchTests(unittest.TestCase):
    def test_optional_apk_crest_is_preserved_without_assuming_format(self):
        base = {'Id': 'opaque', 'Nombre': 'Equipo', 'Club': 'Club', 'Categoria': 'Cat', 'Temporada': '26/27'}
        for value, expected in [(' imagen-opaca ', 'imagen-opaca'), ('', None), (None, None), (42, None), ('x' * 1025, None)]:
            with self.subTest(value=value):
                team = module.normalize_team_results({'error': '', 'equipos': [{**base, 'Escudo': value}]})[0]
                self.assertEqual(team.get('escudo'), expected)

    def test_distinguishes_same_name_by_season_and_category(self):
        teams = [
            {'Id': 'opaque-A', 'Nombre': 'Club Negro', 'Club': 'Club', 'Categoria': 'Alevin', 'Temporada': '26/27'},
            {'Id': 'opaque-B', 'Nombre': 'Club Negro', 'Club': 'Club', 'Categoria': 'Infantil', 'Temporada': '26/27'},
            {'Id': 'opaque-C', 'Nombre': 'Club Negro', 'Club': 'Club', 'Categoria': 'Alevin', 'Temporada': '25/26'},
        ]
        result = module.normalize_team_results({'error': '', 'equipos': teams})
        self.assertEqual([x['id'] for x in result], ['opaque-A', 'opaque-B', 'opaque-C'])
        self.assertEqual([(x['categoria'], x['temporada']) for x in result],
                         [('Alevin', '26/27'), ('Infantil', '26/27'), ('Alevin', '25/26')])

    def test_empty_list_and_invalid_responses(self):
        self.assertEqual(module.normalize_team_results({'error': '', 'equipos': []}), [])
        for response in ({'error': 'rechazado', 'equipos': []}, {'equipos': []},
                         {'error': '', 'equipos': {}}, {'error': '', 'equipos': [{'Id': 'x'}]}):
            with self.subTest(response=response), self.assertRaises(module.TeamSearchError):
                module.normalize_team_results(response)


