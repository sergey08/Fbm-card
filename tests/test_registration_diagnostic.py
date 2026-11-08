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
            with patch.object(module, 'post_device_form', return_value={'key': 'private-key', 'idDispositivo': 'private-id'}) as post, contextlib.redirect_stdout(output):
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
