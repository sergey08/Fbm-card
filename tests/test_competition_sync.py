"""SQLite archive and official FBM group refresh tests without player verification."""
import asyncio
from datetime import date
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/"custom_components/fbm"
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+".py"))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

Archive=load("competition_archive").CompetitionArchive
sync_group=load("competition_sync").sync_group
preview_group=load("competition_sync").preview_group

def identity(season="26/27",group="group1",phase="phase1"):
    return {"season_id":season,"phase_id":phase,"group_id":group,
            "season_verified":True}

class FakeClient:
    def __init__(self):
        self.calls=[]
        self.phase="phase1"
        self.group="group1"
        self.roster_callback=None
    async def async_team_group_identity(self,team):
        self.calls.append("identity")
        return {"phase_id":self.phase,"group_id":self.group,
                "season_verified":False,"season_id":None}
    async def async_team_standings(self,team):
        self.calls.append("standings")
        return {"clasificacion":[{"id":"a","equipo":"A"},{"id":"b","equipo":"B"}]}
    async def async_team_schedule(self,team,start,end):
        self.calls.append("schedule")
        return {"partidos":[{"id":"m1","local":"A","visitante":"B"}]}
    async def async_team_roster(self,team):
        self.calls.append("roster")
        if self.roster_callback:
            self.roster_callback()
        return {"jugadores":[{"id":team+"-p","nombre":"Test",
                              "puntos_totales":5,"foto":"private-photo"}]}
    async def async_verify_group_season(self,teams):
        raise AssertionError("No player queries during regular sync")

class GroupTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.archive=Archive(str(Path(temp.name)/"group.sqlite"))
        self.client=FakeClient()
    def select(self):
        self.archive.follow(identity(),"a")
    def run_sync(self,**kwargs):
        return asyncio.run(sync_group(self.client,self.archive,"a",
                           date(2026,10,1),date(2026,11,1),**kwargs))

    def test_unselected_cannot_read_fixtures_or_rosters(self):
        result=self.run_sync()
        self.assertEqual(result["status"],"not_followed")
        self.assertNotIn("schedule",self.client.calls)
        self.assertNotIn("roster",self.client.calls)

    def test_full_group_without_player_season_checks(self):
        self.select()
        result=self.run_sync()
        self.assertEqual(result["status"],"ok")
        self.assertEqual(result["team_count"],2)
        self.assertEqual(result["rosters_saved"],2)
        saved=self.archive.latest(identity(),"roster","a")["payload"]
        self.assertNotIn("foto",saved["jugadores"][0])
        self.assertNotIn("private-photo",str(saved))
        self.assertIsNotNone(self.archive.latest(identity(),"fixtures"))
        self.assertEqual(self.archive.followed_with_anchor()[0]["season_id"],"26/27")

    def test_refresh_only_fixtures_without_rosters(self):
        self.select()
        result=self.run_sync(fetch_rosters=False)
        self.assertTrue(result["saved"])
        self.assertNotIn("roster",self.client.calls)
        self.assertEqual(self.run_sync(fetch_rosters=False)["records_written"],0)

    def test_changed_phase_aborts_before_schedule(self):
        self.select()
        self.client.phase="another"
        result=self.run_sync(fetch_rosters=True,expected_competition={
            "season_id":"26/27","phase_id":"phase1","group_id":"group1"})
        self.assertEqual(result["status"],"not_followed")
        self.assertNotIn("schedule",self.client.calls)

    def test_expected_season_mismatch_blocks(self):
        self.select()
        result=self.run_sync(fetch_rosters=True,expected_competition={
            "season_id":"25/26","phase_id":"phase1","group_id":"group1"})
        self.assertEqual(result["status"],"competition_changed")
        self.assertNotIn("schedule",self.client.calls)

    def test_revoked_follow_interrupts_rosters(self):
        self.select()
        self.client.roster_callback=lambda:self.archive.unfollow(identity())
        result=self.run_sync()
        self.assertEqual(result["status"],"not_followed")
        self.assertEqual(self.client.calls.count("roster"),1)
        self.assertIsNone(self.archive.latest(identity(),"fixtures"))

    def test_wrong_team_never_accepted_as_group_member(self):
        self.select()
        with self.assertRaises(ValueError):
            asyncio.run(sync_group(self.client,self.archive,"other",
                                   date(2026,10,1),date(2026,11,1)))
        self.assertNotIn("schedule",self.client.calls)

    def test_preview_read_only(self):
        result=asyncio.run(preview_group(self.client,"a",
                             date(2026,10,1),date(2026,11,1)))
        self.assertEqual(result["team_count"],2)
        self.assertEqual(result["match_count"],1)
        self.assertFalse(result["persisted"])
        self.assertEqual(self.archive.followed(),[])

    def test_anchor_deduplication_and_legacy_migration(self):
        self.select()
        self.archive.follow(identity())
        self.assertEqual(len(self.archive.followed()),1)
        self.assertEqual(self.archive.followed_with_anchor()[0]["anchor_team_id"],"a")
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"old.sqlite")
            with sqlite3.connect(path) as db:
                db.execute("""CREATE TABLE competitions(season TEXT NOT NULL,
                 phase TEXT NOT NULL,group_id TEXT NOT NULL,
                 followed INTEGER NOT NULL DEFAULT 1,
                 PRIMARY KEY(season,phase,group_id))""")
                db.execute("INSERT INTO competitions VALUES ('26/27','p','g',1)")
            self.assertEqual(Archive(path).followed_with_anchor()[0]["anchor_team_id"],"")

    def test_sanitization_and_preserved_history(self):
        self.select()
        fixture={"partidos":[{"id":"m","local":"A","visitante":"B",
                "escudo":"secret","marcador":{"local":4,"visitante":2}}]}
        self.archive.record(identity(),"fixtures",fixture)
        self.assertNotIn("secret",str(self.archive.latest(identity(),"fixtures")))
        self.archive.unfollow(identity())
        self.assertIsNotNone(self.archive.latest(identity(),"fixtures"))
        self.assertFalse(self.archive.record(identity(),"fixtures",fixture))

if __name__=="__main__":
    unittest.main()
