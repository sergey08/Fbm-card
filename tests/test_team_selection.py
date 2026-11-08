"""Seleccion local de equipos sin red ni datos privados."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/seleccionar_equipo.py'
spec = importlib.util.spec_from_file_location('team_selection_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TeamSelectionTests(unittest.TestCase):
    def test_list_and_save_exact_distinct_id_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'teams.json', Path(tmp) / 'chosen.json'
            items = [dict(Id='opaque1', Nombre='Club', Club='Club', Categoria='Alevin', Temporada='26/27'),
                     dict(Id='opaque2', Nombre='Club', Club='Club', Categoria='Infantil', Temporada='25/26')]
            source.write_text(json.dumps(items), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(['--equipos', str(source)]), 0)
                self.assertIn('2. Club | Club | Infantil | 25/26', output.getvalue())
                args = ['--equipos', str(source), '--numero', '2', '--salida', str(target)]
                self.assertEqual(module.main(args), 0)
                self.assertEqual(json.loads(target.read_text(encoding='utf-8')), items[1])
                self.assertEqual(module.main(args), 1)
                self.assertEqual(json.loads(target.read_text(encoding='utf-8')), items[1])

    def test_rejects_incomplete_and_out_of_range(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            source, target = Path(tmp) / 'teams.json', Path(tmp) / 'chosen.json'
            source.write_text('[{}]', encoding='utf-8')
            self.assertEqual(module.main(['--equipos', str(source)]), 1)
            source.write_text('[]', encoding='utf-8')
            self.assertEqual(module.main(['--equipos', str(source), '--numero', '1', '--salida', str(target)]), 1)
            self.assertFalse(target.exists())
