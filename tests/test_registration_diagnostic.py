"""Pruebas sin red del diagnóstico de registro invitado."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "scripts/probar_registro_invitado.py"
spec = importlib.util.spec_from_file_location("fbm_registration_diagnostic_test", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RegistrationDiagnosticTests(unittest.TestCase):
    def test_dry_run_does_not_contact_server_or_require_uid(self):
        stdout = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(module, "post_device_form") as post, \
             contextlib.redirect_stdout(stdout):
            result = module.main(["--android-release", "16"])
        self.assertEqual(result, 0)
        self.assertIn("SIN RED", stdout.getvalue())
        post.assert_not_called()

    def test_explicit_send_requires_uid(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(module, "post_device_form") as post, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                module.main(["--android-release", "16", "--enviar"])
        self.assertEqual(raised.exception.code, 2)
        post.assert_not_called()

    def test_explicit_send_uses_exact_fields_and_hides_secrets(self):
        stdout = io.StringIO()
        with patch.dict(os.environ, {"FBM_ANDROID_ID": "private-uid"}), \
             patch.object(module, "post_device_form",
                          return_value={"key": "private-key", "idDispositivo": "private-id"}) as post, \
             contextlib.redirect_stdout(stdout):
            result = module.main(["--android-release", "16", "--enviar"])
        self.assertEqual(result, 0)
        self.assertEqual(post.call_args.args[0], {
            "accion": "registrar", "uid": "private-uid",
            "plataforma": "Android 16", "tipo_dispositivo": "mobile",
            "version": "5.0.42",
        })
        self.assertNotIn("private-uid", stdout.getvalue())
        self.assertNotIn("private-key", stdout.getvalue())
        self.assertNotIn("private-id", stdout.getvalue())

    def test_rejected_response_does_not_leak(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {"FBM_ANDROID_ID": "private-uid"}), \
             patch.object(module, "post_device_form",
                          return_value={"error": "private-server-message"}), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = module.main(["--android-release", "16", "--enviar"])
        self.assertEqual(result, 1)
        self.assertNotIn("private-uid", stderr.getvalue())
        self.assertNotIn("private-server-message", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
