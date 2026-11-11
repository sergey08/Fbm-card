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
