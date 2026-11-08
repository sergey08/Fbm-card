"""Pruebas puras de formularios de dispositivo reconstruidos del APK."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fbm/device_protocol.py"
spec = importlib.util.spec_from_file_location("fbm_device_protocol", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DeviceProtocolTests(unittest.TestCase):
    def test_registration_exact_fields(self):
        self.assertEqual(module.registration_fields(
            uid="u", plataforma="p", tipo_dispositivo="t", version="v"),
            {"accion": "registrar", "uid": "u", "plataforma": "p",
             "tipo_dispositivo": "t", "version": "v"})

    def test_access_exact_fields(self):
        self.assertEqual(module.access_fields(
            uid="u", token_push="", id_dispositivo="d", plataforma="p",
            tipo_dispositivo="t", version="v"),
            {"accion": "acceso", "uid": "u", "token_push": "",
             "id_dispositivo": "d", "plataforma": "p",
             "tipo_dispositivo": "t", "version": "v"})

    def test_extract_identity_from_response(self):
        self.assertEqual(module.extract_identity_fields(
            {"key": "k", "idDispositivo": "d", "error": None}), ("k", "d"))

    def test_reject_incomplete_or_error_response(self):
        for response in (None, {}, {"key": "k"},
                         {"key": "k", "idDispositivo": "d", "error": "fallo"}):
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    module.extract_identity_fields(response)

    def test_missing_uid_rejected(self):
        with self.assertRaises(ValueError):
            module.registration_fields(uid="", plataforma="p",
                                       tipo_dispositivo="t", version="v")

    def test_missing_device_id_rejected(self):
        with self.assertRaises(ValueError):
            module.access_fields(uid="u", token_push="", id_dispositivo="",
                                 plataforma="p", tipo_dispositivo="t", version="v")


if __name__ == "__main__":
    unittest.main()
