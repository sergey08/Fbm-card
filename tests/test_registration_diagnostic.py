import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'scripts/probar_registro_invitado.py'
spec = importlib.util.spec_from_file_location('diagnostic_test', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RegistrationDiagnosticTests(unittest.TestCase):
    def test_dry_run_has_no_network_or_file(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(module, 'post_device_form') as post, contextlib.redirect_stdout(io.StringIO()):
            path = Path(tmp) / 'identity.json'
            self.assertEqual(module.main(['--android-release', '16', '--identidad', str(path)]), 0)
            self.assertFalse(path.exists())
            post.assert_not_called()

    def test_create_persists_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(module, 'post_device_form') as post, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            path = Path(tmp) / 'identity.json'
            args = ['--android-release', '16', '--identidad', str(path), '--crear-identidad']
            self.assertEqual(module.main(args), 0)
            original = path.read_bytes()
            uid = module.load_identity(path)
            self.assertRegex(uid, r'^[0-9a-f]{16}$')
            self.assertEqual(module.main(args), 1)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(module.load_identity(path), uid)
            post.assert_not_called()

    def test_send_uses_persisted_uid_without_leaks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'identity.json'
            module.create_identity(path)
            uid = module.load_identity(path)
            output = io.StringIO()
            with patch.object(module, 'post_device_form', return_value={'error': '', 'key': 'private-key', 'id_dispositivo': 'private-id'}) as post, contextlib.redirect_stdout(output):
                result = module.main(['--android-release', '16', '--identidad', str(path), '--enviar'])
            self.assertEqual(result, 0)
            self.assertEqual(post.call_args.args[0], {'accion': 'registrar', 'uid': uid, 'plataforma': 'Android 16', 'tipo_dispositivo': 'mobile', 'version': '5.0.42'})
            for secret in (uid, 'private-key', 'private-id'):
                self.assertNotIn(secret, output.getvalue())

    def test_invalid_identity_never_sends(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(module, 'post_device_form') as post, contextlib.redirect_stderr(io.StringIO()):
            path = Path(tmp) / 'identity.json'
            path.write_text(json.dumps({'format': 1, 'uid': 'invalid'}))
            self.assertEqual(module.main(['--android-release', '16', '--identidad', str(path), '--enviar']), 1)
            post.assert_not_called()

    def test_server_error_is_hidden(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()) as err:
            path = Path(tmp) / 'identity.json'
            module.create_identity(path)
            with patch.object(module, 'post_device_form', return_value={'error': 'private-server-message'}):
                self.assertEqual(module.main(['--android-release', '16', '--identidad', str(path), '--enviar']), 1)
            self.assertNotIn('private-server-message', err.getvalue())
            self.assertIn('error=texto_no_vacio', err.getvalue())

    def test_field_shapes_do_not_expose_values(self):
        response = {'key': 'private-key', 'dispositivoId': 42, 'error': False}
        self.assertEqual(module.field_shape(response, 'key'), 'texto_no_vacio')
        self.assertEqual(module.field_shape(response, 'idDispositivo'), 'ausente')
        self.assertEqual(module.field_shape(response, 'dispositivoId'), 'numero')
        self.assertEqual(module.field_shape(response, 'error'), 'booleano')

    def test_error_marker_allowlist_does_not_expose_unrecognized_content(self):
        for value, expected in [('false', 'texto_false'), (' 0 ', 'texto_0'),
                                (False, 'booleano_false'), (0, 'numero_0'),
                                ('private-server-message', 'otro_valor_oculto')]:
            with self.subTest(value=value):
                self.assertEqual(module.error_marker({'error': value}), expected)

    def test_observed_shape_remains_unvalidated(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()) as err:
            path = Path(tmp) / 'identity.json'
            module.create_identity(path)
            response = {'key': 'private-key', 'id_dispositivo': 'private-id', 'error': 'false'}
            with patch.object(module, 'post_device_form', return_value=response):
                self.assertEqual(module.main(['--android-release', '16', '--identidad', str(path), '--enviar']), 1)
            self.assertIn('id_dispositivo=texto_no_vacio', err.getvalue())
            self.assertIn('marcador_error=texto_false', err.getvalue())
            self.assertNotIn('private-id', err.getvalue())
            self.assertNotIn('private-key', err.getvalue())

    def test_save_error_only_and_refuse_existing_file_before_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = Path(tmp) / 'identity.json'
            error_path = Path(tmp) / 'error.json'
            module.create_identity(identity)
            response = {'key': 'private-key', 'id_dispositivo': 'private-id', 'error': 'private-error'}
            args = ['--android-release', '16', '--identidad', str(identity), '--enviar', '--guardar-error', str(error_path)]
            with patch.object(module, 'post_device_form', return_value=response) as post, contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(module.main(args), 1)
                self.assertEqual(json.loads(error_path.read_text(encoding='utf-8')), {'error': 'private-error'})
                self.assertNotIn('private-error', out.getvalue() + err.getvalue())
                post.reset_mock()
                self.assertEqual(module.main(args), 1)
                post.assert_not_called()

    def test_save_error_requires_send(self):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(module, 'post_device_form') as post:
            with self.assertRaises(SystemExit):
                module.main(['--android-release', '16', '--guardar-error', 'error.json'])
            post.assert_not_called()

    def test_candidate_access_is_explicit_and_uses_matching_uid(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = Path(tmp) / 'identity.json'
            candidate = Path(tmp) / 'candidate.json'
            module.create_identity(identity)
            uid = module.load_identity(identity)
            registration = {'key': 'secret-key', 'id_dispositivo': 'candidate-id', 'error': 'uuid ya registrado'}
            with patch.object(module, 'post_device_form', return_value=registration) as post, contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                args = ['--android-release', '16', '--identidad', str(identity), '--candidato', str(candidate)]
                self.assertEqual(module.main(args + ['--enviar']), 1)
                self.assertEqual(module.load_candidate(candidate, uid), 'candidate-id')
                self.assertNotIn('secret-key', candidate.read_text())
                post.reset_mock()
                self.assertEqual(module.main(args + ['--acceder']), 1)
                self.assertEqual(post.call_args.args[0]['accion'], 'acceso')
                self.assertEqual(post.call_args.args[0]['id_dispositivo'], 'candidate-id')
                self.assertNotIn('candidate-id', out.getvalue() + err.getvalue())
                other = Path(tmp) / 'other.json'
                module.create_identity(other)
                post.reset_mock()
                self.assertEqual(module.main(['--android-release', '16', '--identidad', str(other), '--candidato', str(candidate), '--acceder']), 1)
                post.assert_not_called()

    def test_existing_candidate_prevents_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = Path(tmp) / 'identity.json'
            candidate = Path(tmp) / 'candidate.json'
            module.create_identity(identity)
            candidate.write_text('existing')
            with patch.object(module, 'post_device_form') as post, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(['--android-release', '16', '--identidad', str(identity), '--candidato', str(candidate), '--enviar']), 1)
                post.assert_not_called()
                self.assertEqual(candidate.read_text(), 'existing')

    def test_search_only_after_unambiguous_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, candidate = Path(tmp) / 'identity.json', Path(tmp) / 'candidate.json'
            module.create_identity(identity)
            module.save_candidate(candidate, module.load_identity(identity), {'id_dispositivo': 'private-id'})
            args = ['--android-release', '16', '--identidad', str(identity), '--candidato', str(candidate), '--buscar-equipo', 'Pinto']
            with patch.object(module, 'post_device_form', return_value={'error': '', 'key': 'private-key', 'id_dispositivo': ''}) as post, patch.object(module, 'search_once', return_value={'equipos': []}) as search, contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(module.main(args), 1)
                self.assertEqual(post.call_args.args[0]['accion'], 'acceso')
                search.assert_called_once_with('private-id', 'private-key', 'Pinto')
                self.assertIn('numero_equipos=0', out.getvalue())
                self.assertNotIn('private-key', out.getvalue())
                self.assertNotIn('private-id', out.getvalue())
            for response in ({'error': 'no', 'key': 'k'}, {'error': '', 'key': ''}, {'error': '', 'key': 'k', 'id_dispositivo': 'other'}):
                with self.subTest(response=response), patch.object(module, 'post_device_form', return_value=response), patch.object(module, 'search_once') as search, contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(module.main(args), 1)
                    search.assert_not_called()

    def test_search_form_is_limited_to_known_fields(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'{"equipos": []}'
        with patch.object(module.protocol, 'open_request', return_value=Response()) as urlopen:
            self.assertEqual(module.search_once('device', 'key', 'Pinto'), {'equipos': []})
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, 'https://appaficionfbm.gesdeportiva.es/v2/busqueda.ashx')
            self.assertEqual(module.urllib.parse.parse_qs(request.data.decode()), {'accion': ['buscarEquipo'], 'id_dispositivo': ['device'], 'key': ['key'], 'texto': ['Pinto'], 'skip': ['0']})

    def test_save_only_team_list_and_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, candidate, teams = (Path(tmp) / name for name in ('identity.json', 'candidate.json', 'teams.json'))
            module.create_identity(identity)
            module.save_candidate(candidate, module.load_identity(identity), {'id_dispositivo': 'device'})
            args = ['--android-release', '16', '--identidad', str(identity), '--candidato', str(candidate), '--buscar-equipo', 'Pinto', '--guardar-equipos', str(teams)]
            with patch.object(module, 'post_device_form', return_value={'error': '', 'key': 'private-key'} ) as post, patch.object(module, 'search_once', return_value={'equipos': [{'nombre': 'Equipo'}], 'key': 'secret'}), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(args), 1)
                self.assertEqual(json.loads(teams.read_text(encoding='utf-8')), [{'nombre': 'Equipo'}])
                post.reset_mock()
                self.assertEqual(module.main(args), 1)
                post.assert_not_called()

    def test_phases_uses_selected_opaque_id_after_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, candidate, team = (Path(tmp) / name for name in ('identity.json', 'candidate.json', 'team.json'))
            module.create_identity(identity)
            module.save_candidate(candidate, module.load_identity(identity), {'id_dispositivo': 'device'})
            team.write_text(json.dumps({'Id': 'opaque-team-id'}), encoding='utf-8')
            args = ['--android-release', '16', '--identidad', str(identity), '--candidato', str(candidate), '--equipo', str(team), '--fases']
            with patch.object(module, 'post_device_form', return_value={'error': '', 'key': 'private-key'}), patch.object(module, 'phases_once', return_value={'error': '', 'fases': []}) as phases, contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(module.main(args), 1)
                phases.assert_called_once_with('device', 'private-key', 'opaque-team-id')
                self.assertNotIn('opaque-team-id', out.getvalue())
                self.assertNotIn('private-key', out.getvalue())

    def test_phases_form_matches_observed_fields(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'{"fases": []}'
        with patch.object(module.protocol, 'open_request', return_value=Response()) as urlopen:
            module.phases_once('device', 'key', 'team')
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, 'https://appaficionfbm.gesdeportiva.es/v2/equipo.ashx')
            self.assertEqual(module.urllib.parse.parse_qs(request.data.decode()), {'accion': ['fasesGrupos'], 'id_dispositivo': ['device'], 'key': ['key'], 'id_equipo': ['team']})

    def test_save_phases_is_explicit_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, candidate, team, target = (Path(tmp) / name for name in ('identity.json', 'candidate.json', 'team.json', 'phases.json'))
            module.create_identity(identity)
            module.save_candidate(candidate, module.load_identity(identity), {'id_dispositivo': 'device'})
            team.write_text(json.dumps({'Id': 'team'}), encoding='utf-8')
            args = ['--android-release', '16', '--identidad', str(identity), '--candidato', str(candidate), '--equipo', str(team), '--fases', '--guardar-fases', str(target)]
            with patch.object(module, 'post_device_form', return_value={'error': '', 'key': 'key'}) as post, patch.object(module, 'phases_once', return_value={'error': '', 'items': [1]}), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(args), 1)
                self.assertEqual(json.loads(target.read_text(encoding='utf-8')), {'error': '', 'items': [1]})
                post.reset_mock()
                self.assertEqual(module.main(args), 1)
                post.assert_not_called()

    def test_schedule_form_matches_current_phase_group_and_date_format(self):
        phases = {'error': '', 'faseActual': 'f', 'grupoActual': 'g', 'listaFasesGrupo': [
            {'IdFase': 'f', 'Grupos': [{'IdGrupo': 'g'}], 'Rondas': []}]}
        form = module.schedule_fields('d', 'k', 't', phases, '2026-11-01', '2026-11-30')
        self.assertEqual(form, {'accion': 'horariosJornadas', 'id_dispositivo': 'd', 'key': 'k',
            'id_equipo': 't', 'id_fase': 'f', 'id_grupo': 'g', 'id_ronda': '',
            'fecha_inicial': '2026-11-01 00:00', 'fecha_final': '2026-11-30 23:59'})
        phases['listaFasesGrupo'][0]['Rondas'] = [{'IdRonda': 'r'}]
        with self.assertRaises(ValueError):
            module.schedule_fields('d', 'k', 't', phases, '2026-11-01', '2026-11-30')

    def test_schedule_invalid_date_prevents_network(self):
        with patch.object(module, 'post_device_form') as post, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                module.main(['--android-release', '16', '--identidad', 'a', '--candidato', 'b', '--equipo', 'c', '--desde', 'bad', '--hasta', '2026-11-01', '--horarios'])
            post.assert_not_called()

    def test_schedule_requires_explicit_access_and_saves_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, candidate, team, target = (Path(tmp) / n for n in ('identity.json', 'candidate.json', 'team.json', 'schedule.json'))
            module.create_identity(identity)
            module.save_candidate(candidate, module.load_identity(identity), {'id_dispositivo': 'device'})
            team.write_text(json.dumps({'Id': 'team'}), encoding='utf-8')
            phases = {'error': '', 'faseActual': 'f', 'grupoActual': 'g', 'listaFasesGrupo': [{'IdFase': 'f', 'Grupos': [{'IdGrupo': 'g'}], 'Rondas': []}]}
            args = ['--android-release', '16', '--identidad', str(identity), '--candidato', str(candidate), '--equipo', str(team), '--desde', '2026-11-01', '--hasta', '2026-11-30', '--horarios', '--guardar-horarios', str(target)]
            with patch.object(module, 'post_device_form', return_value={'error': '', 'key': 'secret'}) as access, patch.object(module, 'phases_once', return_value=phases) as get_phases, patch.object(module, 'schedule_once', return_value={'error': '', 'items': []}) as schedule, contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(args), 1)
                self.assertEqual(access.call_args.args[0]['accion'], 'acceso')
                get_phases.assert_called_once_with('device', 'secret', 'team')
                self.assertEqual(schedule.call_args.args[0]['accion'], 'horariosJornadas')
                self.assertEqual(json.loads(target.read_text(encoding='utf-8')), {'error': '', 'items': []})
                self.assertNotIn('secret', output.getvalue())
                access.reset_mock()
                self.assertEqual(module.main(args), 1)
                access.assert_not_called()

    def test_classification_fields_require_unique_group_and_phase_type(self):
        phases = {'error': '', 'faseActual': 'phase', 'grupoActual': 'group', 'listaFasesGrupo': [
            {'IdFase': 'phase', 'TipoFase': 'LIGA', 'Grupos': [{'IdGrupo': 'group'}]}]}
        self.assertEqual(module.classification_fields('device', 'secret', phases), {
            'accion': 'clasificacion', 'id_dispositivo': 'device', 'key': 'secret',
            'id_grupo': 'group', 'tipo_fase': 'LIGA'})
        phases['listaFasesGrupo'][0]['Grupos'].append({'IdGrupo': 'group'})
        with self.assertRaises(ValueError): module.classification_fields('device', 'secret', phases)

    def test_classification_is_explicit_and_does_not_expose_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, candidate, team, target = (Path(tmp) / n for n in ('identity.json', 'candidate.json', 'team.json', 'classification.json'))
            module.create_identity(identity)
            module.save_candidate(candidate, module.load_identity(identity), {'id_dispositivo': 'private-device'})
            team.write_text(json.dumps({'Id': 'team'}), encoding='utf-8')
            phases = {'error': '', 'faseActual': 'f', 'grupoActual': 'g', 'listaFasesGrupo': [
                {'IdFase': 'f', 'TipoFase': 'LIGA', 'Grupos': [{'IdGrupo': 'g'}]}]}
            args = ['--android-release', '16', '--identidad', str(identity), '--candidato', str(candidate), '--equipo', str(team), '--clasificacion', '--guardar-clasificacion', str(target)]
            with patch.object(module, 'post_device_form', return_value={'error': '', 'key': 'private-key'}) as access, patch.object(module, 'phases_once', return_value=phases), patch.object(module, 'schedule_once', return_value={'error': '', 'clasificacion': []}) as query, contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(args), 1)
                self.assertEqual(query.call_args.args[0]['accion'], 'clasificacion')
                self.assertIn('elementos=0', out.getvalue())
                self.assertNotIn('private-key', out.getvalue())
                self.assertNotIn('private-device', out.getvalue())
                access.reset_mock()
                self.assertEqual(module.main(args), 1)
                access.assert_not_called()

    def test_transport_failure_is_classified_without_secrets(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()) as err:
            path = Path(tmp) / 'identity.json'
            module.create_identity(path)
            with patch.object(module, 'post_device_form', side_effect=module.protocol.DeviceTransportError('http', 403)):
                self.assertEqual(module.main(['--android-release', '16', '--identidad', str(path), '--enviar']), 1)
            self.assertIn('HTTP 403', err.getvalue())
            self.assertNotIn(module.load_identity(path), err.getvalue())

if __name__ == '__main__':
    unittest.main()
