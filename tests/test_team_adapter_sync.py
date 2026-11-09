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

    def test_registration_requires_explicit_call_and_refuses_ambiguous_response(self):
        identity = local_identity_module.IndependentIdentity('0123456789abcdef')
        store = types.SimpleNamespace(async_begin_registration=AsyncMock(return_value=identity), async_bind_candidate=AsyncMock())
        client = independent_module.IndependentClient(store)
        path = package.__name__ + '.independent_client.asyncio.to_thread'
        with patch(path, new=AsyncMock(return_value={'error': 'uuid ya registrado', 'key': 'k', 'id_dispositivo': 'd'})) as post:
            with self.assertRaises(local_identity_module.IdentityError):
                run_immediate(client.async_register('16'))
            post.assert_awaited_once()
            store.async_bind_candidate.assert_not_awaited()
        with patch(path, new=AsyncMock(return_value={'error': '', 'key': 'k', 'id_dispositivo': 'd'})) as post:
            run_immediate(client.async_register('16'))
            self.assertEqual(post.await_args.args[1]['accion'], 'registrar')
            store.async_bind_candidate.assert_awaited_once_with(identity.uid, 'd')

    def test_register_refuses_an_existing_candidate_without_network(self):
        store = types.SimpleNamespace(async_begin_registration=AsyncMock(side_effect=local_identity_module.IdentityError('pending')))
        client = independent_module.IndependentClient(store)
        path = package.__name__ + '.independent_client.asyncio.to_thread'
        with patch(path, new=AsyncMock()) as post:
            with self.assertRaises(local_identity_module.IdentityError):
                run_immediate(client.async_register('16'))
            post.assert_not_awaited()

    def test_uncertain_registration_persists_and_blocks_retry_after_restart(self):
        class MemoryStore:
            def __init__(self): self.data = None
            async def async_load(self): return self.data
            async def async_save(self, data): self.data = dict(data)
        backend = MemoryStore()
        manager = local_identity_module.IndependentIdentityStore(backend)
        client = independent_module.IndependentClient(manager)
        run_immediate(client.async_create_identity())
        uid = backend.data['uid']
        path = package.__name__ + '.independent_client.asyncio.to_thread'
        with patch(path, new=AsyncMock(side_effect=RuntimeError('timeout'))) as post:
            with self.assertRaises(RuntimeError): run_immediate(client.async_register('16'))
            post.assert_awaited_once()
        self.assertEqual(backend.data['registration_state'], 'pending')
        self.assertEqual(backend.data['uid'], uid)
        restarted = independent_module.IndependentClient(local_identity_module.IndependentIdentityStore(backend))
        status = run_immediate(restarted.async_status())
        self.assertTrue(status['registro_pendiente'])
        self.assertNotIn(uid, str(status))
        with patch(path, new=AsyncMock()) as post:
            with self.assertRaises(local_identity_module.IdentityError): run_immediate(restarted.async_register('16'))
            post.assert_not_awaited()
        with patch(path, new=AsyncMock(return_value={'error': 'uuid ya registrado', 'key': 'key', 'id_dispositivo': 'candidate'})) as post:
            run_immediate(restarted.async_recover_registration('16'))
            post.assert_awaited_once()
        self.assertEqual(backend.data['uid'], uid)
        self.assertEqual(backend.data['registration_state'], 'complete')
        self.assertEqual(backend.data['candidate_device_id'], 'candidate')
        with patch(path, new=AsyncMock()) as post:
            with self.assertRaises(local_identity_module.IdentityError): run_immediate(restarted.async_recover_registration('16'))
            post.assert_not_awaited()

    def test_failed_pending_save_prevents_registration_request(self):
        class FailingStore:
            async def async_load(self):
                return {'format': 2, 'uid': '0123456789abcdef', 'candidate_device_id': None, 'registration_state': 'not_started'}
            async def async_save(self, data): raise OSError('storage failed')
        client = independent_module.IndependentClient(local_identity_module.IndependentIdentityStore(FailingStore()))
        path = package.__name__ + '.independent_client.asyncio.to_thread'
        with patch(path, new=AsyncMock()) as post:
            with self.assertRaises(OSError): run_immediate(client.async_register('16'))
            post.assert_not_awaited()

    def test_successful_registration_is_marked_pending_before_post(self):
        class MemoryStore:
            def __init__(self): self.data = None
            async def async_load(self): return self.data
            async def async_save(self, data): self.data = dict(data)
        backend = MemoryStore()
        client = independent_module.IndependentClient(local_identity_module.IndependentIdentityStore(backend))
        run_immediate(client.async_create_identity())
        async def post(*args):
            self.assertEqual(backend.data['registration_state'], 'pending')
            return {'error': '', 'key': 'key', 'id_dispositivo': 'candidate'}
        with patch(package.__name__ + '.independent_client.asyncio.to_thread', new=post):
            run_immediate(client.async_register('16'))
        self.assertEqual(backend.data['registration_state'], 'complete')
        self.assertEqual(backend.data['candidate_device_id'], 'candidate')
        self.assertNotIn('key', backend.data)

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
