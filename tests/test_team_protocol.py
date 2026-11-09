"""Contratos de fases y horarios sin conexiones."""
import importlib.util
from datetime import date
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/fbm'
package = types.ModuleType('fbm_team_protocol_test')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
for name in ('team_phases', 'team_protocol'):
    spec = importlib.util.spec_from_file_location(package.__name__ + '.' + name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
protocol = sys.modules[package.__name__ + '.team_protocol']


class TeamProtocolTests(unittest.TestCase):
    def setUp(self):
        self.phases = {'error': '', 'faseActual': 'f', 'grupoActual': 'g', 'listaFasesGrupo': [
            {'IdFase': 'f', 'NombreFase': 'Phase', 'TipoFase': 'LIGA', 'Grupos': [{'IdGrupo': 'g', 'NombreGrupo': 'Group'}], 'Rondas': []}]}

    def test_form_for_current_unique_phase(self):
        fields = protocol.schedule_fields('device', 'key', 'team', self.phases, date(2026, 11, 1), date(2026, 12, 31))
        self.assertEqual(fields, {'accion': 'horariosJornadas', 'id_dispositivo': 'device', 'key': 'key',
                                  'id_equipo': 'team', 'id_fase': 'f', 'id_grupo': 'g', 'id_ronda': '',
                                  'fecha_inicial': '2026-11-01 00:00', 'fecha_final': '2026-12-31 23:59'})
        self.phases['listaFasesGrupo'][0]['Rondas'] = [{'IdRonda': 'r', 'NombreRonda': 'Final'}]
        still_group = protocol.schedule_fields(
            'device', 'key', 'team', self.phases, date(2026, 11, 1), date(2026, 12, 31))
        self.assertEqual(still_group['id_grupo'], 'g')
        self.assertEqual(still_group['id_ronda'], '')

    def test_explicit_round_uses_round_id_and_empty_group(self):
        self.phases['listaFasesGrupo'][0]['Rondas'] = [{'IdRonda': 'r1', 'NombreRonda': 'Final'}, {'IdRonda': 'r2', 'NombreRonda': 'Semifinal'}]
        form = protocol.schedule_fields('device', 'key', 'team', self.phases, date(2026, 11, 1), date(2026, 12, 31), 'r2')
        self.assertEqual(form['id_fase'], 'f')
        self.assertEqual(form['id_ronda'], 'r2')
        self.assertEqual(form['id_grupo'], '')
        with self.assertRaises(ValueError):
            protocol.schedule_fields('device', 'key', 'team', self.phases, date(2026, 11, 1), date(2026, 12, 31), 'other')

    def test_transport_sends_expected_form_and_rejects_unknown_fields(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return b'{"error":"","listaFasesGrupo":[]}'
        fields = protocol.phases_fields('device', 'key', 'team')
        with patch.object(protocol, 'open_request', return_value=Response()) as urlopen:
            self.assertEqual(protocol.post_team_form(fields)['error'], '')
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, protocol.TEAM_URL)
            self.assertEqual({k: v[0] for k, v in parse_qs(request.data.decode()).items()}, fields)
        with patch.object(protocol, 'open_request') as urlopen:
            with self.assertRaises(ValueError):
                protocol.post_team_form({**fields, 'unexpected': 'x'})
            urlopen.assert_not_called()

    def test_players_post_uses_same_verified_team_endpoint(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return b'{"error":"","misJugadores":[]}'
        form = {'accion':'jugadores', 'id_dispositivo':'device',
                'key':'session', 'id_equipo':'team'}
        with patch.object(protocol, 'open_request', return_value=Response()) as transport:
            result = protocol.post_team_form(form)
        request = transport.call_args.args[0]
        self.assertEqual(request.full_url, protocol.TEAM_URL)
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(result['misJugadores'], [])
        self.assertEqual({k:v[0] for k,v in parse_qs(request.data.decode()).items()}, form)

    def test_invalid_dates_rejected(self):
        with self.assertRaises(ValueError):
            protocol.schedule_fields('d', 'k', 't', self.phases, date(2027, 1, 1), date(2026, 1, 1))

    def test_standings_form_uses_current_group_and_phase_type(self):
        fields = protocol.standings_fields('d', 'k', self.phases)
        self.assertEqual(fields, {'accion': 'clasificacion', 'id_dispositivo': 'd', 'key': 'k',
                                  'id_grupo': 'g', 'tipo_fase': 'LIGA'})
        self.phases['listaFasesGrupo'][0]['TipoFase'] = ''
        with self.assertRaises(ValueError): protocol.standings_fields('d', 'k', self.phases)

    def test_schedule_transport_requires_exactly_one_group_or_round(self):
        self.phases['listaFasesGrupo'][0]['Rondas'] = [{'IdRonda': 'r', 'NombreRonda': 'Final'}]
        form = protocol.schedule_fields('d', 'k', 't', self.phases, date(2026, 11, 1), date(2026, 12, 31), 'r')
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return b'{"error":""}'
        with patch.object(protocol, 'open_request', return_value=Response()) as send:
            protocol.post_team_form(form)
            self.assertEqual(parse_qs(send.call_args.args[0].data.decode(), keep_blank_values=True)['id_grupo'], [''])
        with patch.object(protocol, 'open_request') as send:
            with self.assertRaises(ValueError): protocol.post_team_form({**form, 'id_grupo': 'g'})
            send.assert_not_called()
