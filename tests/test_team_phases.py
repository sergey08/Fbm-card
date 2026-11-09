"""Seleccion de fase y grupo sin red y sin datos reales."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'custom_components/fbm/team_phases.py'
spec = importlib.util.spec_from_file_location('team_phases_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TeamPhasesTests(unittest.TestCase):
    def setUp(self):
        self.data = {'error': '', 'faseActual': 'phase-2', 'grupoActual': 'group-2', 'listaFasesGrupo': [
            {'IdFase': 'phase-1', 'NombreFase': 'Otra', 'Grupos': [], 'Rondas': []},
            {'IdFase': 'phase-2', 'NombreFase': 'Segunda', 'Grupos': [
                {'IdGrupo': 'group-1', 'NombreGrupo': 'A'},
                {'IdGrupo': 'group-2', 'NombreGrupo': 'B'}], 'Rondas': []}]}

    def test_selects_matching_ids_without_relying_on_position(self):
        result = module.current_phase_group(self.data)
        self.assertEqual(result, {'id_fase': 'phase-2', 'nombre_fase': 'Segunda',
                                  'id_grupo': 'group-2', 'nombre_grupo': 'B', 'rondas': []})

    def test_rejects_missing_or_ambiguous_matches(self):
        for modification in ('missing', 'duplicate', 'error'):
            self.setUp()
            if modification == 'missing': self.data['grupoActual'] = 'not-found'
            if modification == 'duplicate': self.data['listaFasesGrupo'][1]['Grupos'].append({'IdGrupo': 'group-2', 'NombreGrupo': 'C'})
            if modification == 'error': self.data['error'] = 'rejected'
            with self.subTest(modification=modification), self.assertRaises(module.TeamPhasesError):
                module.current_phase_group(self.data)

    def test_rounds_require_explicit_selection_and_do_not_require_group(self):
        self.data['grupoActual'] = ''
        self.data['listaFasesGrupo'][1]['Rondas'] = [
            {'IdRonda': 'r1', 'NombreRonda': 'Final'}, {'IdRonda': 'r2', 'NombreRonda': 'Otra'}]
        options = module.phase_options(self.data)
        self.assertEqual([x['nombre'] for x in options['rondas']], ['Final', 'Otra'])
        with self.assertRaises(module.TeamPhasesError): module.schedule_selection(self.data)
        self.assertEqual(module.schedule_selection(self.data, 'r1'), {'id_fase': 'phase-2', 'id_grupo': '', 'id_ronda': 'r1'})
        with self.assertRaises(module.TeamPhasesError): module.schedule_selection(self.data, 'other')
        self.data['listaFasesGrupo'][1]['Rondas'].append({'IdRonda': 'r1', 'NombreRonda': 'Duplicate'})
        with self.assertRaises(module.TeamPhasesError): module.phase_options(self.data)
