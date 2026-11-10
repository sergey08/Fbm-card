"""Offline contract tests for Afición FBM player details."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"
pkg = types.ModuleType("fbm_player_detail_test")
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
for name in ("device_protocol", "player_protocol", "player_detail"):
    spec = importlib.util.spec_from_file_location(pkg.__name__ + "." + name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
mod = sys.modules[pkg.__name__ + ".player_detail"]
protocol = sys.modules[pkg.__name__ + ".player_protocol"]


class PlayerDetailTests(unittest.TestCase):
    def test_form_uses_apk_endpoint_and_existing_session(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return b'{"error":"","jugador":{"id":"p1","nombre":"Prueba"}}'
        fields = protocol.player_detail_fields("device", "key", "p1")
        with patch.object(mod, "open_request", return_value=Response()) as transport:
            payload = mod.post_player_detail_form(fields)
        req = transport.call_args.args[0]
        self.assertEqual(req.full_url, mod.PLAYER_URL)
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual({k: v[0] for k, v in parse_qs(req.data.decode()).items()}, fields)
        self.assertEqual(payload["jugador"]["id"], "p1")

    def test_normalize_removes_private_extra_fields(self):
        payload = {"error": "", "key": "secret", "jugador": {
            "id": "p1", "nombre": "Jugador ejemplo", "puntosTotales": 16,
            "partidosJugados": 3, "foto": "private-photo", "fechaNacimiento": "private-date"}}
        result = mod.normalize_player_detail(payload, "p1")
        self.assertEqual(result["jugador"]["puntos_totales"], 16)
        self.assertNotIn("secret", str(result))
        self.assertNotIn("private", str(result))

    def test_live_pascalcase_detail_with_missing_total_points(self):
        response={"error":"","jugador":{
            "Id":"p1","Nombre":"Jugador ejemplo","NombreEquipo":"Equipo",
            "Temporada":"26/27","Categoria":"Senior",
            "PartidosJugados":5,"PuntosTotales":-1,
            "MediaPuntos":7,"PuntosPorPartido":7.0,
            "MinutosPorPartido":12.5,"Foto":"private-image"}}
        result=mod.normalize_player_detail(response,"p1")["jugador"]
        self.assertEqual(result["nombre"],"Jugador ejemplo")
        self.assertEqual(result["partidos_jugados"],5)
        self.assertIsNone(result["puntos_totales"])
        self.assertEqual(result["minutos_por_partido"],12.5)
        self.assertNotIn("Foto",result)
        self.assertNotIn("private-image",str(result))

    def test_mixed_detail_case_and_mismatched_id_rejected(self):
        for response in (
            {"error":"","jugador":{"Id":"p1","Nombre":"Player","puntosTotales":2}},
            {"error":"","jugador":{"Id":"wrong","Nombre":"Player"}},
            {"error":"","jugador":{"Id":"p1","Nombre":"Player","PuntosTotales":-2}},
        ):
            with self.assertRaises(mod.PlayerDetailError):
                mod.normalize_player_detail(response,"p1")

    def test_reject_mismatched_id_or_bad_stats(self):
        for data in (
            {"error": "", "jugador": {"id": "other", "nombre": "Prueba"}},
            {"error": "", "jugador": {"id": "p1", "nombre": "Prueba", "puntosTotales": True}},
            {"error": "", "jugador": {"id": "p1", "nombre": "Prueba", "puntosTotales": -1}},
            {"error": "", "jugador": None},
        ):
            with self.subTest(data=str(data)[:30]), self.assertRaises(mod.PlayerDetailError):
                mod.normalize_player_detail(data, "p1")

    def test_reject_unapproved_form_before_traffic(self):
        with patch.object(mod, "open_request") as transport:
            with self.assertRaises(ValueError):
                mod.post_player_detail_form({
                    "accion": "registrar", "id_dispositivo": "device",
                    "key": "session", "id_jugador": "p1"
                })
            transport.assert_not_called()


if __name__ == "__main__":
    unittest.main()
