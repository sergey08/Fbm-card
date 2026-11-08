"""Pruebas aisladas del adaptador FBM; no hay conexiones de red."""
import asyncio
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"
package = types.ModuleType("fbm_adapter_test_pkg")
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
for name in ("guest_identity", "aficion_adapter"):
    spec = importlib.util.spec_from_file_location(
        package.__name__ + "." + name, ROOT / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from fbm_adapter_test_pkg.aficion_adapter import (
    AficionFBMAdapter, FBMAccessNotValidated, FBMRequestError, _post_search
)
from fbm_adapter_test_pkg.guest_identity import GuestIdentity


class FakeResponse:
    status = 200
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass
    def read(self, n):
        return self.data[:n]


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_unvalidated_access(self):
        adapter = AficionFBMAdapter()
        with self.assertRaises(FBMAccessNotValidated):
            await adapter.query("jornada", {"competicion": 1, "grupo": 2, "jornada": 3})

    async def test_without_identity_does_not_contact_server(self):
        with patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(FBMAccessNotValidated):
                await AficionFBMAdapter().search("buscarEquipo", "Pinto")
            urlopen.assert_not_called()

    async def test_search_fields_sent_as_form(self):
        identity = GuestIdentity.from_response(
            "dummy", "device", datetime.now(timezone.utc)
        )
        with patch("urllib.request.urlopen", return_value=FakeResponse(b'{"resultado":"ok"}')) as urlopen:
            result = await AficionFBMAdapter(identity).search("buscarEquipo", "Pinto")
            self.assertEqual(result["resultado"], "ok")
            request = urlopen.call_args.args[0]
            from urllib.parse import parse_qs
            fields = parse_qs(request.data.decode())
            self.assertEqual(fields["accion"], ["buscarEquipo"])
            self.assertEqual(fields["id_dispositivo"], ["device"])
            self.assertEqual(fields["key"], ["dummy"])
            self.assertEqual(fields["texto"], ["Pinto"])

    async def test_non_json_rejected(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"not-json")):
            with self.assertRaises(FBMRequestError):
                _post_search({"accion": "buscarEquipo"})

    async def test_oversized_response_rejected(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"x" * (128 * 1024 + 1))):
            with self.assertRaises(FBMRequestError):
                _post_search({"accion": "buscarEquipo"})


if __name__ == "__main__":
    unittest.main()
