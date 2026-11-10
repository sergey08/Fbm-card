"""Pruebas aisladas del registro Lovelace sin instalar Home Assistant."""
import asyncio
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "fbm"


def module(name, **attrs):
    obj = types.ModuleType(name)
    obj.__dict__.update(attrs)
    sys.modules[name] = obj
    return obj


# Sustitutos mínimos para probar el comportamiento, no la API real de HA.
module("homeassistant")
module("homeassistant.components")
module("homeassistant.components.http", StaticPathConfig=lambda *a, **kw: (a, kw))
module("homeassistant.components.lovelace")
module("homeassistant.components.lovelace.const", DOMAIN="lovelace")
module("homeassistant.core", HomeAssistant=object, callback=lambda fn: fn)
module("homeassistant.config_entries", ConfigEntry=object)
module("homeassistant.helpers")
module("homeassistant.helpers.storage", Store=MagicMock())
module("probatio", Required=lambda key, default=None: key, Schema=lambda schema: schema, In=lambda choices: choices)
module("homeassistant.components.websocket_api",
       websocket_command=lambda schema: lambda function: function,
       require_admin=lambda function: function,
       async_response=lambda function: function,
       async_register_command=MagicMock())
module("custom_components")
module("custom_components.fbm").__path__ = [str(PKG)]

spec = importlib.util.spec_from_file_location(
    "custom_components.fbm", PKG / "__init__.py",
    submodule_search_locations=[str(PKG)],
)
fbm = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fbm
spec.loader.exec_module(fbm)


class IdentitySetupTests(unittest.TestCase):
    def test_entry_creates_manager_without_loading_or_saving_identity(self):
        hass = MagicMock()
        hass.data = {}
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        entry = types.SimpleNamespace(entry_id='example', options={},
            add_update_listener=lambda cb: lambda: None,
            async_on_unload=lambda action: None)
        store = MagicMock()
        with patch.object(fbm, 'Store', return_value=store) as factory:
            coro = fbm.async_setup_entry(hass, entry)
            with self.assertRaises(StopIteration) as result:
                coro.send(None)
        self.assertTrue(result.exception.value)
        self.assertEqual(factory.call_count, 2)
        factory.assert_any_call(hass, 1, 'fbm.identity.example', private=True, atomic_writes=True)
        factory.assert_any_call(hass, 1, 'fbm.recovery.example', private=True, atomic_writes=True)
        store.async_load.assert_called_once()
        store.async_save.assert_not_called()
        self.assertIn('identidad_independiente', hass.data['fbm']['example'])
        self.assertIn('grupos_sqlite_path', hass.data['fbm']['example'])



class SessionRestoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_saved_profile_reuses_existing_device_without_registration(self):
        identity = MagicMock()
        identity.async_load = AsyncMock(return_value=types.SimpleNamespace(
            uid="0123456789abcdef", candidate_device_id="existing-device"))
        profile = MagicMock()
        profile.async_load = AsyncMock(return_value={"format": 1, "android_release": "16"})
        profile.async_save = AsyncMock()
        client = fbm.IndependentClient(identity, recovery_store=profile)
        from custom_components.fbm.independent_client import AficionFBMAdapter
        with patch.object(AficionFBMAdapter, "access_with_profile", new_callable=AsyncMock) as access:
            access.return_value.session_is_usable.return_value = True
            self.assertTrue(await client.async_restore())
        access.assert_awaited_once()
        profile.async_save.assert_awaited_once_with({"format": 1, "android_release": "16"})
        identity.async_load.assert_awaited_once()

    async def test_missing_profile_causes_no_network_or_identity_mutation(self):
        identity = MagicMock()
        identity.async_load = AsyncMock()
        profile = MagicMock()
        profile.async_load = AsyncMock(return_value=None)
        client = fbm.IndependentClient(identity, recovery_store=profile)
        from custom_components.fbm.independent_client import AficionFBMAdapter
        with patch.object(AficionFBMAdapter, "access_with_profile", new_callable=AsyncMock) as access:
            self.assertFalse(await client.async_restore())
        identity.async_load.assert_not_awaited()
        access.assert_not_awaited()
        profile.async_save.assert_not_called()

    async def test_access_failure_is_nonfatal_and_does_not_reregister(self):
        identity = MagicMock()
        identity.async_load = AsyncMock(return_value=types.SimpleNamespace(
            uid="0123456789abcdef", candidate_device_id="existing-device"))
        profile = MagicMock()
        profile.async_load = AsyncMock(return_value={"format": 1, "android_release": "16"})
        profile.async_save = AsyncMock()
        client = fbm.IndependentClient(identity, recovery_store=profile)
        from custom_components.fbm.independent_client import AficionFBMAdapter
        with patch.object(AficionFBMAdapter, "access_with_profile", new_callable=AsyncMock,
                          side_effect=OSError("network down")):
            self.assertFalse(await client.async_restore())
        profile.async_save.assert_not_awaited()

class ResourceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.resources = MagicMock()
        self.resources.async_load = AsyncMock()
        self.resources.async_create_item = AsyncMock()
        self.hass = MagicMock()
        self.hass.data = {"lovelace": types.SimpleNamespace(resources=self.resources)}

    async def test_register_once(self):
        self.resources.async_items.return_value = []
        self.assertTrue(await fbm._async_register_lovelace_resource(self.hass))
        self.resources.async_create_item.assert_awaited_once_with(
            {"res_type": "module", "url": "/fbm_static/fbm-card.js"}
        )

    async def test_existing_resource_not_duplicated(self):
        self.resources.async_items.return_value = [
            {"url": "/fbm_static/fbm-card.js?v=1", "type": "module"}
        ]
        self.assertTrue(await fbm._async_register_lovelace_resource(self.hass))
        self.resources.async_create_item.assert_not_awaited()

    async def test_missing_lovelace_resources(self):
        self.hass.data = {}
        self.assertFalse(await fbm._async_register_lovelace_resource(self.hass))

    async def test_resource_error_is_nonfatal(self):
        self.resources.async_items.return_value = []
        self.resources.async_create_item.side_effect = ValueError("storage disabled")
        self.assertFalse(await fbm._async_register_lovelace_resource(self.hass))

    async def test_storage_io_error_is_nonfatal(self):
        self.resources.async_load.side_effect = OSError("storage unavailable")
        self.assertFalse(await fbm._async_register_lovelace_resource(self.hass))
        self.resources.async_create_item.assert_not_awaited()

    async def test_missing_bundled_card_fails_setup(self):
        self.hass.http.async_register_static_paths = AsyncMock()
        with patch.object(pathlib.Path, "is_file", return_value=False):
            self.assertFalse(await fbm.async_setup(self.hass, {}))
        self.hass.http.async_register_static_paths.assert_not_awaited()

    async def test_missing_card_registers_no_websocket_commands(self):
        self.hass.http.async_register_static_paths = AsyncMock()
        from homeassistant.components import websocket_api
        with patch.object(pathlib.Path, "is_file", return_value=False), patch.object(
            websocket_api, "async_register_command"
        ) as register:
            self.assertFalse(await fbm.async_setup(self.hass, {}))
        register.assert_not_called()

    async def test_setup_registers_expected_websocket_commands(self):
        self.hass.http.async_register_static_paths = AsyncMock()
        from homeassistant.components import websocket_api
        expected = {
            "ws_entries", "ws_status", "ws_create", "ws_register",
            "ws_recover", "ws_connect", "ws_search", "ws_schedule",
            "ws_phases", "ws_schedule_round", "ws_standings", "ws_group_identity", "ws_schedule_probe", "ws_roster", "ws_player_detail", "ws_player_stats", "ws_diagnostic", "ws_player_detail_diagnostic", "ws_player_stats_diagnostic", "ws_competition_sync", "ws_competition_list", "ws_competition_latest", "ws_competition_preview", "ws_competition_analysis", "ws_competition_verify_season", "ws_competition_player_stats_batch",
        }
        with patch.object(websocket_api, "async_register_command") as register:
            self.assertTrue(await fbm.async_setup(self.hass, {}))
        self.assertEqual(register.call_count, len(expected))
        self.assertEqual(
            {call.args[1].__name__ for call in register.call_args_list},
            expected,
        )
        self.assertTrue(all(call.args[0] is self.hass for call in register.call_args_list))

    async def test_card_static_path_is_served(self):
        self.hass.http.async_register_static_paths = AsyncMock()
        self.assertTrue(await fbm.async_setup(self.hass, {}))
        self.hass.http.async_register_static_paths.assert_awaited_once()
        config = self.hass.http.async_register_static_paths.await_args.args[0][0]
        self.assertEqual(config[0][0], "/fbm_static/fbm-card.js")


if __name__ == "__main__":
    unittest.main()
