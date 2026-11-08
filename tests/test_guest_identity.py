"""Pruebas del plazo local deducido del APK, sin tráfico externo."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fbm/guest_identity.py"
spec = importlib.util.spec_from_file_location("fbm_guest_identity_test", PATH)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)
GuestIdentity = module.GuestIdentity


class GuestIdentityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        self.identity = GuestIdentity.from_response("test-key", "test-device", self.now)

    def test_exact_duration(self):
        self.assertEqual(self.identity.key_until_ms - module.utc_epoch_ms(self.now), 84_400_000)

    def test_key_before_and_at_boundary(self):
        before = self.now + timedelta(milliseconds=84_399_999)
        at = self.now + timedelta(milliseconds=84_400_000)
        self.assertEqual(self.identity.key_for_request(before), "test-key")
        self.assertEqual(self.identity.key_for_request(at), "")

    def test_fields_and_empty_key_after_window(self):
        at = self.now + timedelta(milliseconds=84_400_000)
        self.assertEqual(self.identity.search_fields("buscarEquipo", "Pinto", 0, at),
                         {"accion": "buscarEquipo", "id_dispositivo": "test-device",
                          "key": "", "texto": "Pinto", "skip": "0"})

    def test_reject_unverified_action_and_negative_skip(self):
        with self.assertRaises(ValueError):
            self.identity.search_fields("otro", "Pinto", 0, self.now)
        with self.assertRaises(ValueError):
            self.identity.search_fields("buscarClub", "Pinto", -1, self.now)

    def test_reject_naive_datetime(self):
        with self.assertRaises(ValueError):
            module.utc_epoch_ms(datetime(2026, 11, 8))


if __name__ == "__main__":
    unittest.main()
