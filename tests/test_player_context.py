"""Strict player stats context tests: synthetic official detail DTO only."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).resolve().parents[1]/"custom_components/fbm/player_context.py"
spec=importlib.util.spec_from_file_location("player_context",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def detail():
    return {"error":"","jugador":{"id":"p","nombre":"Prueba"},
            "equipo":{"id":"t","nombre":"Equipo de prueba"},
            "idComponenteClub":"c","idTemporadaActual":"s",
            "key":"private-session", "foto":"private"}

class PlayerContextTests(unittest.TestCase):
    def test_exact_binding_only_and_no_personal_fields(self):
        result=mod.verified_player_stats_context(detail(),"p","t")
        self.assertEqual(result,{"id_jugador":"p","id_equipo":"t",
                                 "id_componente_club":"c","id_temporada":"s"})
        self.assertNotIn("private",repr(result))
        self.assertNotIn("Prueba",repr(result))

    def test_rejects_wrong_team_or_player(self):
        for player, team in (("x","t"),("p","other")):
            with self.subTest(player=player,team=team), self.assertRaises(mod.PlayerContextUnverified):
                mod.verified_player_stats_context(detail(),player,team)

    def test_missing_ids_do_not_create_fake_associations(self):
        for key,value in (("idComponenteClub",None),("idTemporadaActual",""),
                          ("equipo",None),("jugador",None),("idTemporadaActual",True)):
            raw=detail();raw[key]=value
            with self.subTest(key=key),self.assertRaises(mod.PlayerContextUnverified):
                mod.verified_player_stats_context(raw,"p","t")

    def test_no_silent_fallback_to_display_names_or_search_season(self):
        raw=detail();raw.pop("equipo");raw["nombreEquipo"]="Equipo de prueba"
        raw["temporada"]="2026/2027"
        with self.assertRaises(mod.PlayerContextUnverified):
            mod.verified_player_stats_context(raw,"p","t")

    def test_rejects_error_response_and_untrusted_payload_type(self):
        for raw in ({"error":"no",**detail()}, ["secret"], None):
            if isinstance(raw,dict):raw["error"]="no"
            with self.assertRaises(mod.PlayerContextUnverified):
                mod.verified_player_stats_context(raw,"p","t")
if __name__=="__main__":unittest.main()
