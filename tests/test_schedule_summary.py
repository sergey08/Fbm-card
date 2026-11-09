"""Resumen local sin exposicion de claves ni identificadores."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/resumir_horarios.py'
spec = importlib.util.spec_from_file_location('schedule_summary_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ScheduleSummaryTests(unittest.TestCase):
    def test_summary_excludes_session_and_match_identifiers(self):
        data = {'error': '', 'key': 'private-key', 'id_dispositivo': 'private-device', 'jornadaActual': 4,
                'partidos': [{'IdPartido': 'private-match', 'NombreEquipoLocal': 'Equipo A',
                              'NombreEquipoVisitante': 'Equipo B', 'NumeroJornada': 5,
                              'Fecha': '2026-11-09', 'Hora': '10:00'}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'schedule.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(module.main([str(path)]), 0)
            self.assertIn('Equipo A - Equipo B', output.getvalue())
            for secret in ('private-key', 'private-device', 'private-match'):
                self.assertNotIn(secret, output.getvalue())

    def test_rejects_server_error_and_incomplete_data(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            path = Path(tmp) / 'schedule.json'
            for data in ({'error': 'failed', 'partidos': []}, {'error': '', 'partidos': [{}]}):
                path.write_text(json.dumps(data), encoding='utf-8')
                self.assertEqual(module.main([str(path)]), 1)

    def test_optional_filter_matches_either_side_and_preserves_group_count(self):
        data = {'error': '', 'partidos': [
            {'NombreEquipoLocal': 'Pinto', 'NombreEquipoVisitante': 'A'},
            {'NombreEquipoLocal': 'B', 'NombreEquipoVisitante': 'PINTO'},
            {'NombreEquipoLocal': 'C', 'NombreEquipoVisitante': 'D'}]}
        with tempfile.TemporaryDirectory() as tmp:
            path, team = Path(tmp) / 'schedule.json', Path(tmp) / 'team.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            team.write_text(json.dumps({'Nombre': 'pinto'}), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(module.main([str(path), '--equipo', str(team)]), 0)
            self.assertIn('2 de 3', output.getvalue())
            self.assertNotIn('C - D', output.getvalue())
