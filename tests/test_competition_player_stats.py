"""Five-player stats batch offline tests with safe opt-in and SQLite."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]/"custom_components"/"fbm"
PACKAGE = "fbm_stats_test_pkg"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package

def load(name):
    spec=importlib.util.spec_from_file_location(PACKAGE + "." + name,ROOT/(name+".py"))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
Archive=load("competition_archive").CompetitionArchive
sync=load("competition_player_stats").sync_player_stats_batch

IDENTITY={"season_verified":True,"season_id":"26/27",
          "phase_id":"phase","group_id":"group"}

class Client:
    def __init__(self):
        self.calls=[]
    async def async_player_statistics(self,player_id,team_id):
        self.calls.append(player_id)
        return {"jugador":player_id,"equipo":team_id,
                "globales":{"estadisticas":{"puntos_totales":None,
                       "media_puntos":None,"rebotes":None}},
                "partidos":{"partidos":[{"id_partido":f"match-{player_id}",
                    "fecha":"2026-11-01","rival":"Otro equipo","local":True,
                    "puntos":9,"faltas_cometidas":2,"valoracion":11,
                    "asistencias":None}]}} 

class StatsTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.archive=Archive(str(Path(tmp.name)/"test.sqlite"))
        self.client=Client()
        self.archive.follow(IDENTITY,"team-A")
        self.archive.record(IDENTITY,"roster",{"jugadores":[
            {"id":str(i),"nombre":f"Jugador {i}",
             "foto":"never-store"} for i in range(9)]},subject="team-A")

    def run_batch(self,offset=0,limit=5):
        return asyncio.run(sync(self.client,self.archive,IDENTITY,
                                "team-A",offset,limit))

    def test_five_player_limit_and_saved_match_scores(self):
        result=self.run_batch()
        self.assertEqual(result["status"],"ok")
        self.assertEqual(result["processed"],5)
        self.assertEqual(result["saved"],5)
        self.assertEqual(result["players_queried"],5)
        self.assertEqual(result["players_zero_appearances"],0)
        self.assertEqual(result["next_offset"],5)
        self.assertEqual(len(self.client.calls),5)
        row=self.archive.latest(IDENTITY,"player_stats","0")
        self.assertEqual(row["payload"]["partidos"][0]["puntos"],9)
        self.assertEqual(row["payload"]["globales"]["puntos_totales"],None)
        self.assertNotIn("Jugador",repr(row))
        self.assertNotIn("never-store",repr(row))
        result=self.run_batch(offset=5)
        self.assertEqual(result["processed"],4)
        self.assertIsNone(result["next_offset"])
        self.assertEqual(self.run_batch()["saved"],0)

    def test_already_archived_appearances_skip_unnecessary_network(self):
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": str(i), "nombre": f"Jugador {i}",
             "partidos_jugados": 1} for i in range(9)
        ]}, subject="team-A")
        first = self.run_batch()
        self.assertEqual(first["saved"], 5)
        self.assertEqual(len(self.client.calls), 5)
        second = self.run_batch()
        self.assertEqual(second["skipped_unchanged"], 5)
        self.assertEqual(second["players_cached_complete"], 5)
        self.assertEqual(second["players_queried"], 0)
        self.assertEqual(second["saved"], 0)
        self.assertEqual(len(self.client.calls), 5)

    def test_new_appearance_refreshes_only_player_with_change(self):
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": str(i), "nombre": f"Jugador {i}",
             "partidos_jugados": 1} for i in range(9)
        ]}, subject="team-A")
        self.run_batch()
        # A single player gets an additional recorded appearance.
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": str(i), "nombre": f"Jugador {i}",
             "partidos_jugados": 2 if i == 3 else 1}
            for i in range(9)
        ]}, subject="team-A")
        second = self.run_batch()
        self.assertEqual(second["skipped_unchanged"], 4)
        self.assertEqual(self.client.calls.count("3"), 2)
        self.assertEqual(len(self.client.calls), 6)

    def test_zero_appearance_player_is_skipped_without_api_error(self):
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": str(i), "nombre": f"Jugador {i}",
             "partidos_jugados": 0 if i in (1, 4) else 1}
            for i in range(9)
        ]}, subject="team-A")
        result = self.run_batch()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["skipped_unchanged"], 2)
        self.assertEqual(result["players_zero_appearances"], 2)
        self.assertEqual(result["players_queried"], 3)
        self.assertEqual(result["saved"], 3)
        self.assertEqual(self.client.calls, ["0", "2", "3"])

    def test_first_appearance_enables_deferred_player_fetch(self):
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": str(i), "nombre": f"Jugador {i}",
             "partidos_jugados": 0 if i == 1 else 1}
            for i in range(9)
        ]}, subject="team-A")
        self.run_batch()
        self.assertNotIn("1", self.client.calls)
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": str(i), "nombre": f"Jugador {i}",
             "partidos_jugados": 1}
            for i in range(9)
        ]}, subject="team-A")
        result = self.run_batch()
        self.assertEqual(result["saved"], 1)
        self.assertEqual(result["skipped_unchanged"], 4)
        self.assertEqual(self.client.calls.count("1"), 1)

    def test_periodic_recheck_fetches_even_if_appearances_unchanged(self):
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": str(i), "nombre": f"Jugador {i}",
             "partidos_jugados": 1} for i in range(9)]},
             subject="team-A")
        self.run_batch()
        self.assertEqual(len(self.client.calls), 5)
        second = asyncio.run(sync(self.client, self.archive, IDENTITY,
                                  "team-A", offset=0, limit=5,
                                  force_recheck=True))
        self.assertEqual(second["status"], "ok")
        self.assertEqual(len(self.client.calls), 10)
        self.assertEqual(second["saved"], 0)
        self.assertEqual(second["skipped_unchanged"], 0)
        self.assertIsNotNone(self.archive.latest(IDENTITY,"player_stats","0"))

    def test_full_recheck_still_skips_zero_game_player(self):
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": "0", "nombre": "Sin partido", "partidos_jugados": 0},
            {"id": "1", "nombre": "Con partido", "partidos_jugados": 1}]},
            subject="team-A")
        result = asyncio.run(sync(self.client, self.archive, IDENTITY,
                                  "team-A", force_recheck=True))
        self.assertEqual(result["status"],"ok")
        self.assertEqual(result["skipped_unchanged"],1)
        self.assertEqual(self.client.calls,["1"])

    def test_incomplete_cache_is_counted_and_refetched(self):
        self.archive.record(IDENTITY, "roster", {"jugadores": [
            {"id": "0", "partidos_jugados": 2}]}, subject="team-A")
        self.archive.record(IDENTITY, "player_stats", {
            "partidos": [{"id_partido": "old", "puntos": None}],
            "globales": {}}, subject="0")
        result = self.run_batch()
        self.assertEqual(result["players_incomplete_cache"], 1)
        self.assertEqual(result["players_queried"], 1)
        self.assertEqual(result["errors"], 0)

    def test_null_match_points_are_reported(self):
        async def missing_points(player_id, team_id):
            return {"jugador": player_id, "equipo": team_id,
                    "globales": {"estadisticas": {}},
                    "partidos": {"partidos": [
                        {"id_partido": "match-null", "puntos": None}]}}
        self.client.async_player_statistics = missing_points
        result = self.run_batch(limit=1)
        self.assertEqual(result["players_missing_points"], 1)
        self.assertEqual(result["players_queried"], 1)
        self.assertEqual(result["errors"], 0)

    def test_no_roster_for_unselected_team(self):
        result=asyncio.run(sync(self.client,self.archive,IDENTITY,"another"))
        self.assertEqual(result["status"],"no_roster")
        self.assertEqual(self.client.calls,[])

    def test_stop_following_blocks_requests(self):
        self.archive.unfollow(IDENTITY)
        result=self.run_batch()
        self.assertEqual(result["status"],"not_followed")
        self.assertEqual(self.client.calls,[])

    def test_invalid_batch_limit(self):
        for count in (0,6,-1):
            with self.assertRaises(ValueError):
                self.run_batch(limit=count)

    def test_wrong_player_team_binding_rejected(self):
        async def mismatch(player_id,team_id):
            return {"jugador":"wrong","equipo":team_id,
                    "globales":{"estadisticas":{}},"partidos":{"partidos":[]}}
        self.client.async_player_statistics=mismatch
        result=self.run_batch(limit=1)
        self.assertEqual(result["status"],"partial")
        self.assertEqual(result["saved"],0)
        self.assertEqual(result["errors"],1)
        self.assertIsNone(self.archive.latest(IDENTITY,"player_stats","0"))

if __name__=="__main__":
    unittest.main()
