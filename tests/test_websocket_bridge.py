"""Pruebas aisladas del puente, con simulaciones de Home Assistant."""
from datetime import date
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/fbm'
package = types.ModuleType('fbm_ws_test')
package.__path__ = [str(ROOT)]
probatio = types.ModuleType('probatio')
probatio.Required = lambda key: key
ha = types.ModuleType('homeassistant')
components = types.ModuleType('homeassistant.components')
websocket = types.ModuleType('homeassistant.components.websocket_api')
websocket.websocket_command = lambda schema: lambda function: function
websocket.async_response = lambda function: function
websocket.async_register_command = MagicMock()
def require_admin(function):
    async def wrapped(hass, connection, msg):
        if not connection.user.is_admin:
            raise PermissionError('admin required')
        return await function(hass, connection, msg)
    return wrapped
websocket.require_admin = require_admin
components.websocket_api = websocket
with patch.dict(sys.modules, {'fbm_ws_test': package, 'probatio': probatio, 'homeassistant': ha,
                             'homeassistant.components': components, 'homeassistant.components.websocket_api': websocket}):
    spec = importlib.util.spec_from_file_location('fbm_ws_test.websocket', ROOT / 'websocket.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def run_immediate(coro):
    try: coro.send(None)
    except StopIteration as done: return done.value
    raise AssertionError('Operacion simulada suspendida')


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.client = types.SimpleNamespace(async_register=AsyncMock(), async_recover_registration=AsyncMock(), async_search_teams=AsyncMock(return_value=[{'nombre': 'A'}]),
            async_team_phase_options=AsyncMock(return_value={'nombre_fase': 'Final', 'rondas': [{'id': 'r', 'nombre': 'Final'}]}),
            async_team_schedule=AsyncMock(return_value={'partidos': []}),
            async_team_schedule_probe=AsyncMock(return_value={'shape':'object','recognized':['partidos'],'entry_fields':[],'counts':{'partidos':0},'has_error':False}),
            async_team_standings=AsyncMock(return_value={'clasificacion': []}),
            async_team_roster=AsyncMock(return_value={'jugadores': [], 'total': 0}),
            async_player_detail_diagnostic=AsyncMock(return_value={'ok':False,'stage':'normalize','shape':{'present':['Jugador']}}),
            async_player_detail=AsyncMock(return_value={'jugador':{'id':'p1','nombre':'Prueba'},'fuente':'FBM'}),
            async_player_statistics_diagnostic=AsyncMock(return_value={'ok':False,'stage':'context'}),
            async_player_statistics=AsyncMock(return_value={'jugador':'p1','equipo':'team','globales':{},'partidos':{}}),
            async_team_diagnostic=AsyncMock(return_value={'ok': False, 'stage': 'normalize', 'category': 'invalid_payload_or_parameters'}),
            async_team_group_identity=AsyncMock(return_value={'group_id':'g','season_id':None,'season_verified':False}))
        self.hass = types.SimpleNamespace(data={'fbm': {'entry': {'cliente_independiente': self.client}}})
        self.connection = types.SimpleNamespace(user=types.SimpleNamespace(is_admin=True), send_result=MagicMock(), send_error=MagicMock())

    def test_admin_required_for_all_commands(self):
        self.connection.user.is_admin = False
        for command in (module.ws_entries, module.ws_status, module.ws_create, module.ws_register, module.ws_recover, module.ws_connect, module.ws_search, module.ws_schedule, module.ws_phases, module.ws_schedule_round, module.ws_standings, module.ws_group_identity, module.ws_schedule_probe, module.ws_roster, module.ws_player_detail, module.ws_player_stats, module.ws_diagnostic, module.ws_player_detail_diagnostic, module.ws_player_stats_diagnostic):
            with self.subTest(command=command), self.assertRaises(PermissionError):
                run_immediate(command(self.hass, self.connection, {'id': 1, 'entry_id': 'entry'}))
        self.client.async_register.assert_not_awaited()

    def test_entries_omits_unrelated_runtime_values(self):
        self.hass.data['fbm']['unrelated'] = {'secret': 'hidden'}
        run_immediate(module.ws_entries(self.hass, self.connection, {'id': 1}))
        self.connection.send_result.assert_called_once_with(1, {'entries': ['entry']})

    def test_registration_is_explicit_and_returns_no_credentials(self):
        run_immediate(module.ws_register(self.hass, self.connection, {'id': 1, 'entry_id': 'entry', 'android_release': '16'}))
        self.client.async_register.assert_awaited_once_with('16')
        self.connection.send_result.assert_called_once_with(1, {'candidato_guardado': True})

    def test_recovery_requires_separate_explicit_command(self):
        run_immediate(module.ws_recover(self.hass, self.connection, {'id': 2, 'entry_id': 'entry', 'android_release': '16'}))
        self.client.async_recover_registration.assert_awaited_once_with('16')
        self.client.async_register.assert_not_awaited()

    def test_search_and_schedule_validate_input(self):
        run_immediate(module.ws_search(self.hass, self.connection, {'id': 2, 'entry_id': 'entry', 'texto': '  Equipo ', 'skip': 0}))
        self.client.async_search_teams.assert_awaited_once_with('Equipo', 0)
        run_immediate(module.ws_schedule(self.hass, self.connection, {'id': 3, 'entry_id': 'entry', 'equipo': 'team', 'desde': '2026-11-01', 'hasta': '2026-12-31'}))
        self.client.async_team_schedule.assert_awaited_once_with('team', date(2026, 11, 1), date(2026, 12, 31))
        run_immediate(module.ws_search(self.hass, self.connection, {'id': 4, 'entry_id': 'entry', 'texto': 'x', 'skip': True}))
        self.connection.send_error.assert_called_once()
        self.assertEqual(self.client.async_search_teams.await_count, 1)

    def test_error_details_and_bad_entry_not_exposed(self):
        self.client.async_register.side_effect = ValueError('secret-identity')
        run_immediate(module.ws_register(self.hass, self.connection, {'id': 1, 'entry_id': 'entry', 'android_release': '16'}))
        self.assertNotIn('secret-identity', str(self.connection.send_error.call_args))
        run_immediate(module.ws_register(self.hass, self.connection, {'id': 2, 'entry_id': 'missing', 'android_release': '16'}))
        self.assertEqual(self.client.async_register.await_count, 1)

    def test_round_request_and_phase_options(self):
        run_immediate(module.ws_phases(self.hass, self.connection, {'id': 1, 'entry_id': 'entry', 'equipo': 'team'}))
        self.client.async_team_phase_options.assert_awaited_once_with('team')
        run_immediate(module.ws_schedule_round(self.hass, self.connection, {'id': 2, 'entry_id': 'entry', 'equipo': 'team', 'ronda': 'r', 'desde': '2026-11-01', 'hasta': '2026-12-31'}))
        self.client.async_team_schedule.assert_awaited_once_with('team', date(2026, 11, 1), date(2026, 12, 31), 'r')

    def test_group_identity_is_read_only_and_requires_valid_team(self):
        run_immediate(module.ws_group_identity(self.hass, self.connection,
            {'id': 9, 'entry_id': 'entry', 'equipo': 'official-team-id'}))
        self.client.async_team_group_identity.assert_awaited_once_with('official-team-id')
        self.connection.send_result.assert_called_once_with(
            9, {'group_id':'g','season_id':None,'season_verified':False})
        run_immediate(module.ws_group_identity(self.hass, self.connection,
            {'id': 10, 'entry_id': 'entry', 'equipo': '  '}))
        self.connection.send_error.assert_called_once()
        self.assertEqual(self.client.async_team_group_identity.await_count, 1)

    def test_roster_query_uses_existing_client_and_requires_admin(self):
        run_immediate(module.ws_roster(self.hass, self.connection,
            {'id': 20, 'entry_id': 'entry', 'equipo': 'team'}))
        self.client.async_team_roster.assert_awaited_once_with('team')
        self.connection.send_result.assert_called_once_with(
            20, {'jugadores': [], 'total': 0})
        run_immediate(module.ws_roster(self.hass, self.connection,
            {'id': 21, 'entry_id': 'entry', 'equipo': ' '}))
        self.connection.send_error.assert_called_once()

    def test_player_detail_requires_admin_and_valid_player_id(self):
        run_immediate(module.ws_player_detail(self.hass, self.connection,
            {'id': 30, 'entry_id': 'entry', 'jugador': 'p1'}))
        self.client.async_player_detail.assert_awaited_once_with('p1')
        run_immediate(module.ws_player_detail(self.hass, self.connection,
            {'id': 31, 'entry_id': 'entry', 'jugador': ' '}))
        self.connection.send_error.assert_called_once()

    def test_stats_requires_admin_and_exact_player_team_pair(self):
        run_immediate(module.ws_player_stats(self.hass, self.connection,
            {'id': 40, 'entry_id': 'entry', 'jugador': 'p1', 'equipo': 'team'}))
        self.client.async_player_statistics.assert_awaited_once_with('p1','team')
        run_immediate(module.ws_player_stats(self.hass, self.connection,
            {'id': 41, 'entry_id': 'entry', 'jugador': ' ', 'equipo': 'team'}))
        self.connection.send_error.assert_called_once()
        self.assertEqual(self.client.async_player_statistics.await_count, 1)

    def test_safe_team_diagnostic_is_admin_only(self):
        run_immediate(module.ws_diagnostic(self.hass, self.connection,
            {'id': 60, 'entry_id': 'entry', 'equipo': 'team', 'kind': 'roster'}))
        self.client.async_team_diagnostic.assert_awaited_once_with('team', 'roster')
        self.connection.send_result.assert_called_once()
        self.assertNotIn('secret', str(self.connection.send_result.call_args))

    def test_admin_player_detail_diagnostic(self):
        run_immediate(module.ws_player_detail_diagnostic(self.hass, self.connection,
            {'id': 71, 'entry_id': 'entry', 'jugador': 'official-id'}))
        self.client.async_player_detail_diagnostic.assert_awaited_once_with('official-id')
        self.connection.send_result.assert_called_once()
        self.assertNotIn('secret', str(self.connection.send_result.call_args))

    def test_stats_diagnostic_is_admin_gated(self):
        run_immediate(module.ws_player_stats_diagnostic(self.hass, self.connection,
            {'id': 91, 'entry_id': 'entry', 'jugador': 'p', 'equipo': 't'}))
        self.client.async_player_statistics_diagnostic.assert_awaited_once_with('p', 't')
        self.connection.send_result.assert_called_once()

    def test_standings_request_is_explicit_and_validated(self):
        run_immediate(module.ws_standings(self.hass, self.connection, {'id': 1, 'entry_id': 'entry', 'equipo': 'team'}))
        self.client.async_team_standings.assert_awaited_once_with('team')
        self.connection.send_result.assert_called_once_with(1, {'clasificacion': []})
        run_immediate(module.ws_standings(self.hass, self.connection, {'id': 2, 'entry_id': 'entry', 'equipo': ' '}))
        self.assertEqual(self.client.async_team_standings.await_count, 1)


