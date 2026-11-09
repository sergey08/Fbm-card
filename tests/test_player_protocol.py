"""Contract-only tests; no real FBM requests or personal/player data."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components/fbm/player_protocol.py"
spec = importlib.util.spec_from_file_location("player_protocol", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PlayerProtocolTests(unittest.TestCase):
    def test_players_form_matches_observed_apk_literals(self):
        fields = mod.players_fields("device", "session", "team")
        self.assertEqual(fields, {
            "accion": "jugadores", "id_dispositivo": "device",
            "key": "session", "id_equipo": "team"
        })

    def test_detail_form_matches_observed_apk_literals(self):
        fields = mod.player_detail_fields("device", "session", "player")
        self.assertEqual(fields, {
            "accion": "detalleJugador", "id_dispositivo": "device",
            "key": "session", "id_jugador": "player"
        })

    def test_invalid_team_and_player_ids_are_rejected(self):
        for field_builder in (mod.players_fields, mod.player_detail_fields):
            for value in ("", "   ", True, 4, "x" * 513):
                with self.subTest(builder=field_builder.__name__, value=str(value)[:10]):
                    with self.assertRaises(ValueError):
                        field_builder("device", "session", value)

    def test_technical_session_cannot_be_missing(self):
        with self.assertRaises(ValueError):
            mod.players_fields("", "session", "team")
        with self.assertRaises(ValueError):
            mod.player_detail_fields("device", "", "player")

if __name__ == "__main__":
    unittest.main()
