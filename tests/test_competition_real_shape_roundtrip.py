"""Six-team, 30-fixture competition roundtrip through actual DEV modules.

Anonymous synthetic scores with the verified REAL FBM group dimensions
(6 teams, 30 schedule entries and 12 finished matches). Does not connect
to FBM, store minors, or modify Home Assistant production.
"""
import asyncio
from datetime import date
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest

BASE=Path(__file__).resolve().parents[1]/"custom_components"/"fbm"

PACKAGE = "fbm_roundtrip_test_pkg"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(BASE)]
sys.modules[PACKAGE] = package

def load(name):
    spec=importlib.util.spec_from_file_location(PACKAGE + "." + name,BASE/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

Archive=load("competition_archive").CompetitionArchive
sync=load("competition_sync").sync_group
analyze=load("competition_analysis").competition_analysis

class Client:
    def __init__(self):
        self.calls=[]
        self.teams=[{"id":str(i),"equipo":f"Equipo {i}","posicion":i,
                     "jugados":4,"ganados":max(0,5-i),"perdidos":min(4,i-1)}
                    for i in range(1,7)]
    async def async_team_group_identity(self, team):
        self.calls.append("identity")
        return {"phase_id":"phase","group_id":"group","season_id":None,
                "season_verified":False}
    async def async_team_standings(self, team):
        self.calls.append("standings")
        return {"clasificacion":self.teams}
    async def async_team_schedule(self,team,start,end):
        self.calls.append("schedule")
        fixtures=[]
        for i in range(30):
            home=i%6+1
            visitor=(i+1+(i//6))%6+1
            if home==visitor: visitor=visitor%6+1
            finished=i<12
            fixtures.append({"id":f"m{i}","local":f"Equipo {home}",
                             "visitante":f"Equipo {visitor}",
                             "estado":"finished" if finished else "scheduled",
                             "fecha":f"2026-11-{(i%28)+1:02d}",
                             "marcador":{"local":30+i,"visitante":25+i}
                             if finished else None})
        return {"partidos":fixtures}
    async def async_team_roster(self,team):
        raise AssertionError("Roster request not permitted by fixture-only sync")
    async def async_verify_group_season(self,teams):
        raise AssertionError("Player detail verification should remain optional")

class RoundTrip(unittest.TestCase):
    def test_six_team_thirty_match_archival_and_analysis(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=Archive(str(Path(folder)/"fbm.sqlite"))
            key={"season_id":"26/27","phase_id":"phase","group_id":"group",
                 "season_verified":True}
            archive.follow(key,"1")
            client=Client()
            result=asyncio.run(sync(client,archive,"1",
                               date(2026,9,1),date(2026,12,1),
                               fetch_rosters=False,
                               expected_competition={k:key[k] for k in
                                    ("season_id","phase_id","group_id")}))
            self.assertEqual(result["status"],"ok")
            self.assertEqual(result["fixture_count"],30)
            self.assertEqual(result["team_count"],6)
            self.assertEqual(result["rosters_saved"],0)
            reopened=Archive(archive.path)
            standing=reopened.latest(key,"standings")["payload"]
            fixtures=reopened.latest(key,"fixtures")["payload"]
            self.assertEqual(len(fixtures["partidos"]),30)
            report=analyze(standing,fixtures)
            self.assertEqual(report["numero_equipos"],6)
            self.assertEqual(report["partidos_con_marcador"],12)
            self.assertEqual(report["plantillas_disponibles"],0)
            self.assertEqual(len(report["anotadores"]),0)
            self.assertEqual(client.calls,["identity","standings","schedule"])
            result=asyncio.run(sync(client,reopened,"1",date(2026,9,1),
                                   date(2026,12,1),fetch_rosters=False))
            self.assertEqual(result["records_written"],0)

if __name__=="__main__":
    unittest.main()
