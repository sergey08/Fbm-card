"""Verify reconnection with the persisted device and a simulated transport."""
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

PACKAGE = "fbm_session_restore_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/fbm")]
sys.modules[PACKAGE] = package
client_module = importlib.import_module(f"{PACKAGE}.independent_client")
identity_module = importlib.import_module(f"{PACKAGE}.independent_identity")


class GuestRestoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_restart_recovers_same_device_on_next_query(self):
        identity = identity_module.IndependentIdentity("0123456789abcdef", "saved-device", "complete")
        identity_store = types.SimpleNamespace(async_load=AsyncMock(return_value=identity))
        recovery_store = types.SimpleNamespace(
            async_load=AsyncMock(return_value={"format": 1, "android_release": "15"}),
            async_save=AsyncMock(),
        )
        adapter = types.SimpleNamespace(
            session_is_usable=lambda: True, search_teams=AsyncMock(return_value=[]),
        )
        client = client_module.IndependentClient(identity_store, recovery_store=recovery_store)
        with (
            patch.object(client_module, "monotonic", side_effect=[100, 100, 101, 131]),
            patch.object(client_module.AficionFBMAdapter, "access_with_profile",
                         side_effect=[OSError("offline"), adapter]) as access,
            patch.object(client_module, "post_device_form") as register,
        ):
            self.assertFalse(await client.async_restore())
            with self.assertRaises(client_module.FBMAccessNotValidated):
                await client.async_search_teams("pinto")
            self.assertEqual(access.await_count, 1)
            self.assertEqual(await client.async_search_teams("pinto"), [])
            self.assertEqual(access.await_count, 2)
            profile, device = access.await_args.args
            self.assertEqual((profile.uid, profile.plataforma, device),
                             (identity.uid, "Android 15", "saved-device"))
            register.assert_not_called()

    async def test_unconfigured_query_does_not_contact_service(self):
        recovery_store = types.SimpleNamespace(async_load=AsyncMock(return_value=None))
        client = client_module.IndependentClient(None, recovery_store=recovery_store)
        with patch.object(client_module.AficionFBMAdapter, "access_with_profile") as access:
            with self.assertRaises(client_module.FBMAccessNotValidated):
                await client.async_search_teams("pinto")
            access.assert_not_called()
