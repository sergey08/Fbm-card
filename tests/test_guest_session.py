"""Pruebas sin red de orquestación de sesión invitada."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"
package = types.ModuleType("fbm_session_test_pkg")
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
for name in ("device_protocol", "guest_identity", "guest_session"):
    spec = importlib.util.spec_from_file_location(
        package.__name__ + "." + name, ROOT / (name + ".py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

from fbm_session_test_pkg.guest_session import DeviceProfile, register_guest, access_guest


class GuestSessionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.profile = DeviceProfile(
            uid="test-uid", plataforma="test-platform",
            tipo_dispositivo="test-type", version="test-version"
        )

    async def test_register_returns_identity(self):
        with patch("fbm_session_test_pkg.guest_session.post_device_form",
                   return_value={"key": "k", "idDispositivo": "d"}) as post:
            identity = await register_guest(self.profile)
        self.assertEqual(identity.key, "k")
        self.assertEqual(identity.device_id, "d")
        self.assertEqual(post.call_args.args[0]["accion"], "registrar")

    async def test_access_requires_matching_device(self):
        with patch("fbm_session_test_pkg.guest_session.post_device_form",
                   return_value={"key": "k", "idDispositivo": "other"}):
            with self.assertRaises(ValueError):
                await access_guest(self.profile, "expected")

    async def test_access_uses_supplied_id(self):
        with patch("fbm_session_test_pkg.guest_session.post_device_form",
                   return_value={"key": "k", "idDispositivo": "d"}) as post:
            identity = await access_guest(self.profile, "d")
        self.assertEqual(identity.device_id, "d")
        self.assertEqual(post.call_args.args[0]["id_dispositivo"], "d")
        self.assertEqual(post.call_args.args[0]["accion"], "acceso")

    def test_android_phone_profile_exact_fields(self):
        profile = DeviceProfile.from_android_phone(
            android_id="abc123", android_release="16")
        self.assertEqual(profile.uid, "abc123")
        self.assertEqual(profile.plataforma, "Android 16")
        self.assertEqual(profile.tipo_dispositivo, "mobile")
        self.assertEqual(profile.version, "5.0.42")

    def test_android_phone_requires_real_values(self):
        with self.assertRaises(ValueError):
            DeviceProfile.from_android_phone(android_id="", android_release="16")
        with self.assertRaises(ValueError):
            DeviceProfile.from_android_phone(android_id="abc", android_release="")

    def test_missing_uid_rejected(self):
        with self.assertRaises(ValueError):
            DeviceProfile(uid="", plataforma="p", tipo_dispositivo="t", version="v")


if __name__ == "__main__":
    unittest.main()
