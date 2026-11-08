"""Pruebas puras de formularios de dispositivo reconstruidos del APK."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

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



class DeviceTransportTests(unittest.TestCase):
    def test_reject_unknown_action_without_network(self):
        with patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(ValueError):
                module.post_device_form({"accion": "otra"})
            urlopen.assert_not_called()

    def test_post_form_exact_endpoint(self):
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, limit):
                return b'{"key":"dummy","idDispositivo":"device"}'
        with patch("urllib.request.urlopen", return_value=Response()) as urlopen:
            result = module.post_device_form(module.registration_fields(
                uid="u", plataforma="p", tipo_dispositivo="t", version="v"))
            self.assertEqual(result["idDispositivo"], "device")
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, module.DEVICE_URL)
            self.assertEqual(parse_qs(request.data.decode())["accion"], ["registrar"])

    def test_incomplete_form_rejected_without_network(self):
        with patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(ValueError):
                module.post_device_form({"accion": "registrar"})
            urlopen.assert_not_called()

    def test_extra_field_rejected_without_network(self):
        fields = module.registration_fields(
            uid="u", plataforma="p", tipo_dispositivo="t", version="v")
        fields["unexpected"] = "x"
        with patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(ValueError):
                module.post_device_form(fields)
            urlopen.assert_not_called()

    def test_bad_json_rejected(self):
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, limit):
                return b'not-json'
        with patch("urllib.request.urlopen", return_value=Response()):
            with self.assertRaises(RuntimeError):
                module.post_device_form(module.access_fields(uid="u", token_push="", id_dispositivo="d", plataforma="p", tipo_dispositivo="t", version="v"))

if __name__ == "__main__":
    unittest.main()
