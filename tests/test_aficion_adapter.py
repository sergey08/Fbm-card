"""Pruebas aisladas del adaptador FBM; no hay conexiones de red."""
import asyncio
import importlib.util
import sys
import types
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"
package = types.ModuleType("fbm_adapter_test_pkg")
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
for name in ("device_protocol", "guest_identity", "guest_session", "aficion_adapter"):
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
    async def test_schedule_uses_phases_and_normalizes_without_extra_network(self):
        identity = GuestIdentity.from_response('secret', 'device', datetime.now(timezone.utc))
        phases = {'error': '', 'faseActual': 'f', 'grupoActual': 'g', 'listaFasesGrupo': [
            {'IdFase': 'f', 'NombreFase': 'Phase', 'Grupos': [{'IdGrupo': 'g', 'NombreGrupo': 'Group'}], 'Rondas': []}]}
        schedule = {'error': '', 'jornadaActual': 4, 'partidos': [{'IdPartido': 'm', 'NombreEquipoLocal': 'A',
                    'NombreEquipoVisitante': 'B', 'Estado': 'Terminado',
                    'Resultados': {'ResultadoLocal': '32', 'ResultadoVisitante': '57'}}]}
        with patch('fbm_adapter_test_pkg.aficion_adapter.asyncio.to_thread', new=AsyncMock(side_effect=[phases, schedule])) as call:
            result = await AficionFBMAdapter(identity).team_schedule('team', date(2026, 11, 1), date(2026, 12, 31))
        self.assertEqual(call.await_count, 2)
        self.assertEqual(call.await_args_list[0].args[1]['accion'], 'fasesGrupos')
        self.assertEqual(call.await_args_list[1].args[1]['accion'], 'horariosJornadas')
        self.assertEqual(result['partidos'][0]['marcador'], {'local': 32, 'visitante': 57})

    async def test_schedule_invalid_dates_never_contact_server(self):
        identity = GuestIdentity.from_response('secret', 'device', datetime.now(timezone.utc))
        with patch('fbm_adapter_test_pkg.aficion_adapter.asyncio.to_thread', new=AsyncMock()) as call:
            with self.assertRaises(ValueError):
                await AficionFBMAdapter(identity).team_schedule('team', date(2026, 12, 1), date(2026, 11, 1))
            call.assert_not_awaited()
    async def test_no_unvalidated_access(self):
        adapter = AficionFBMAdapter()
        with self.assertRaises(FBMAccessNotValidated):
            await adapter.query("jornada", {"competicion": 1, "grupo": 2, "jornada": 3})

    async def test_without_identity_does_not_contact_server(self):
        with patch("fbm_adapter_test_pkg.aficion_adapter.open_request") as urlopen:
            with self.assertRaises(FBMAccessNotValidated):
                await AficionFBMAdapter().search("buscarEquipo", "Pinto")
            urlopen.assert_not_called()

    async def test_search_fields_sent_as_form(self):
        identity = GuestIdentity.from_response(
            "dummy", "device", datetime.now(timezone.utc)
        )
        with patch("fbm_adapter_test_pkg.aficion_adapter.open_request", return_value=FakeResponse(b'{"resultado":"ok"}')) as urlopen:
            result = await AficionFBMAdapter(identity).search("buscarEquipo", "Pinto")
            self.assertEqual(result["resultado"], "ok")
            request = urlopen.call_args.args[0]
            from urllib.parse import parse_qs
            fields = parse_qs(request.data.decode())
            self.assertEqual(fields["accion"], ["buscarEquipo"])
            self.assertEqual(fields["id_dispositivo"], ["device"])
            self.assertEqual(fields["key"], ["dummy"])
            self.assertEqual(fields["texto"], ["Pinto"])

    async def test_explicit_registration_connects_to_search(self):
        from fbm_adapter_test_pkg.guest_session import DeviceProfile
        profile = DeviceProfile(uid="u", plataforma="p",
                                tipo_dispositivo="t", version="5.0.42")
        with patch("fbm_adapter_test_pkg.guest_session.post_device_form",
                   return_value={"key": "k", "idDispositivo": "d"}) as register:
            adapter = await AficionFBMAdapter.register_with_profile(profile)
        self.assertEqual(register.call_args.args[0]["accion"], "registrar")
        with patch("fbm_adapter_test_pkg.aficion_adapter._post_search",
                   return_value={"resultado": "ok"}) as search:
            result = await adapter.search("buscarEquipo", "Pinto")
        self.assertEqual(result, {"resultado": "ok"})
        self.assertEqual(search.call_args.args[0]["key"], "k")
        self.assertEqual(search.call_args.args[0]["id_dispositivo"], "d")

    async def test_explicit_access_connects_to_search(self):
        from fbm_adapter_test_pkg.guest_session import DeviceProfile
        profile = DeviceProfile(uid="u", plataforma="p",
                                tipo_dispositivo="t", version="5.0.42")
        with patch("fbm_adapter_test_pkg.guest_session.post_device_form",
                   return_value={"key": "new-key", "id_dispositivo": "", "error": ""}):
            adapter = await AficionFBMAdapter.access_with_profile(profile, "known")
        with patch("fbm_adapter_test_pkg.aficion_adapter._post_search",
                   return_value={"resultado": "ok"}) as search:
            await adapter.search("buscarClub", "Pinto")
        self.assertEqual(search.call_args.args[0]["accion"], "buscarClub")
        self.assertEqual(search.call_args.args[0]["key"], "new-key")

    async def test_access_mismatch_prevents_search(self):
        from fbm_adapter_test_pkg.guest_session import DeviceProfile
        profile = DeviceProfile(uid="u", plataforma="p",
                                tipo_dispositivo="t", version="5.0.42")
        with patch("fbm_adapter_test_pkg.guest_session.post_device_form",
                   return_value={"key": "k", "id_dispositivo": "other", "error": ""}):
            with patch("fbm_adapter_test_pkg.aficion_adapter._post_search") as search:
                with self.assertRaises(ValueError):
                    await AficionFBMAdapter.access_with_profile(profile, "known")
                search.assert_not_called()

    async def test_non_json_rejected(self):
        with patch("fbm_adapter_test_pkg.aficion_adapter.open_request", return_value=FakeResponse(b"not-json")):
            with self.assertRaises(FBMRequestError):
                _post_search({"accion": "buscarEquipo"})

    async def test_oversized_response_rejected(self):
        with patch("fbm_adapter_test_pkg.aficion_adapter.open_request", return_value=FakeResponse(b"x" * (128 * 1024 + 1))):
            with self.assertRaises(FBMRequestError):
                _post_search({"accion": "buscarEquipo"})


if __name__ == "__main__":
    unittest.main()
