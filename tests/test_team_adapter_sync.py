"""Prueba aislada de orquestacion con tareas simuladas sin bucle ni red."""
from datetime import date, datetime, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/fbm'
package = types.ModuleType('fbm_team_adapter_sync_test')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
for name in ('device_protocol', 'guest_identity', 'guest_session', 'team_search', 'team_phases', 'team_protocol', 'team_schedule', 'aficion_adapter', 'independent_identity', 'independent_client'):
    spec = importlib.util.spec_from_file_location(package.__name__ + '.' + name, ROOT / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
adapter_module = sys.modules[package.__name__ + '.aficion_adapter']
identity_module = sys.modules[package.__name__ + '.guest_identity']
independent_module = sys.modules[package.__name__ + '.independent_client']
local_identity_module = sys.modules[package.__name__ + '.independent_identity']


def run_immediate(coro):
    try:
        coro.send(None)
    except StopIteration as done:
        return done.value
    raise AssertionError('La operacion simulada no deberia suspenderse')


class TeamAdapterSyncTests(unittest.TestCase):
    def test_client_connection_is_explicit_and_does_not_expose_identity(self):
        identity = local_identity_module.IndependentIdentity('0123456789abcdef', 'private-device')
        store = types.SimpleNamespace(async_load=AsyncMock(return_value=identity), async_create=AsyncMock())
        adapter = types.SimpleNamespace(search_teams=AsyncMock(return_value=[{'nombre': 'A'}]))
        client = independent_module.IndependentClient(store)
        connect_path = package.__name__ + '.independent_client.AficionFBMAdapter.access_with_profile'
        with patch(connect_path, new=AsyncMock(return_value=adapter)) as connect:
            with self.assertRaises(adapter_module.FBMAccessNotValidated):
                run_immediate(client.async_search_teams('A'))
            connect.assert_not_awaited()
            run_immediate(client.async_connect('16'))
            profile = connect.await_args.args[0]
            self.assertNotIn(identity.uid, repr(profile))
            self.assertNotIn(identity.candidate_device_id, repr(identity))
            self.assertEqual(run_immediate(client.async_search_teams('A')), [{'nombre': 'A'}])
            run_immediate(client.async_disconnect())
            with self.assertRaises(adapter_module.FBMAccessNotValidated):
                run_immediate(client.async_search_teams('A'))

    def test_failed_reconnect_clears_previous_session(self):
        identity = local_identity_module.IndependentIdentity('0123456789abcdef', 'device')
        client = independent_module.IndependentClient(types.SimpleNamespace(async_load=AsyncMock(return_value=identity)))
        client._adapter = object()
        path = package.__name__ + '.independent_client.AficionFBMAdapter.access_with_profile'
        with patch(path, new=AsyncMock(side_effect=ValueError('rejected'))):
            with self.assertRaises(ValueError): run_immediate(client.async_connect('16'))
        with self.assertRaises(adapter_module.FBMAccessNotValidated):
            run_immediate(client.async_search_teams('A'))

    def test_two_explicit_mocked_calls_return_normalized_schedule(self):
        identity = identity_module.GuestIdentity.from_response('key', 'device', datetime.now(timezone.utc))
        phases = {'error': '', 'faseActual': 'f', 'grupoActual': 'g', 'listaFasesGrupo': [
            {'IdFase': 'f', 'NombreFase': 'Phase', 'Grupos': [{'IdGrupo': 'g', 'NombreGrupo': 'Group'}], 'Rondas': []}]}
        schedule = {'error': '', 'jornadaActual': 1, 'partidos': [
            {'IdPartido': 'm', 'NombreEquipoLocal': 'A', 'NombreEquipoVisitante': 'B', 'Estado': 'Terminado',
             'Resultados': {'ResultadoLocal': '12', 'ResultadoVisitante': '7'}}]}
        with patch.object(adapter_module.asyncio, 'to_thread', new=AsyncMock(side_effect=[phases, schedule])) as transport:
            coroutine = adapter_module.AficionFBMAdapter(identity).team_schedule('team', date(2026, 11, 1), date(2026, 12, 31))
            with self.assertRaises(StopIteration) as done:
                coroutine.send(None)
        self.assertEqual(transport.await_count, 2)
        self.assertEqual(transport.await_args_list[0].args[1]['accion'], 'fasesGrupos')
        self.assertEqual(transport.await_args_list[1].args[1]['accion'], 'horariosJornadas')
        self.assertEqual(done.exception.value['partidos'][0]['marcador'], {'local': 12, 'visitante': 7})
