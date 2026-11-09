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
for name in ('device_protocol', 'guest_identity', 'guest_session', 'team_search', 'team_phases', 'team_protocol', 'team_schedule', 'aficion_adapter'):
    spec = importlib.util.spec_from_file_location(package.__name__ + '.' + name, ROOT / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
adapter_module = sys.modules[package.__name__ + '.aficion_adapter']
identity_module = sys.modules[package.__name__ + '.guest_identity']


class TeamAdapterSyncTests(unittest.TestCase):
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
