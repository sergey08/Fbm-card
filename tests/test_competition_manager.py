"""Official FBM search season and optional cross-team diagnostic."""
import asyncio
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).resolve().parents[1]/"custom_components/fbm/competition_manager.py"
spec=importlib.util.spec_from_file_location("fbm_competition_manager",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeClient:
    def __init__(self):
        self.calls=[]

    async def async_team_group_identity(self, team):
        self.calls.append("identity")
        return {"phase_id":"phase","group_id":"group","season_verified":False}

    async def async_team_standings(self, team):
        self.calls.append("standings")
        return {"clasificacion":[{"id":"a"},{"id":"b"}]}

    async def async_verify_group_season(self, teams):
        self.calls.append("player_diagnostic")
        return {"season_verified":True}


class ManagerTests(unittest.TestCase):
    def test_official_label_select_without_players(self):
        client=FakeClient()
        result=asyncio.run(mod.identify_competition(client,"a","26/27"))
        self.assertEqual(result["season_id"],"26/27")
        self.assertEqual(result["season_source"],"official_team_search")
        self.assertEqual(result["status"],"verified")
        self.assertEqual(client.calls,["identity","standings"])
        self.assertEqual(mod.group_selection(result),{
            "season_id":"26/27","phase_id":"phase",
            "group_id":"group","season_verified":True})

    def test_absent_or_invalid_search_season_rejected(self):
        for value in (None,"2026/2027","26/29","2026","", "26/27;DROP"):
            with self.subTest(value=value):
                client=FakeClient()
                if value is None:
                    result=asyncio.run(mod.identify_competition(client,"a"))
                    self.assertEqual(result["status"],"season_unverified")
                else:
                    with self.assertRaises(ValueError):
                        asyncio.run(mod.identify_competition(client,"a",value))
                self.assertEqual(client.calls,[])
        for value in ("99/00","00/01","26/27"):
            self.assertEqual(mod.official_season_label(value),value)

    def test_group_membership_required(self):
        client=FakeClient()
        with self.assertRaises(ValueError):
            asyncio.run(mod.identify_competition(client,"unlisted","26/27"))
        self.assertEqual(client.calls,["identity","standings"])

    def test_optional_diagnostic_only_when_called(self):
        client=FakeClient()
        result=asyncio.run(mod.competition_season_diagnostic(client,"a"))
        self.assertTrue(result["season_match_verified"])
        self.assertEqual(client.calls,["identity","standings","player_diagnostic"])
        self.assertNotIn("season_id",result)

    def test_no_follow_without_verified_search_label(self):
        with self.assertRaises(ValueError):
            mod.group_selection({"status":"season_unverified"})

if __name__=="__main__":
    unittest.main()
