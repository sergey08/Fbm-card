"""Competition manager verification tests: no FBM network and no HA config changes."""
import asyncio
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components/fbm/competition_manager.py"
spec = importlib.util.spec_from_file_location("fbm_competition_manager", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class OfficialTeamClient:
    def __init__(self, season="official-season", team_id="a"):
        self.season = season
        self.team_id = team_id
        self.calls = []

    async def async_team_group_identity(self, team_id):
        self.calls.append("identity")
        return {"phase_id": "f", "group_id": "g", "season_verified": False}

    async def async_team_standings(self, team_id):
        self.calls.append("standings")
        return {"clasificacion": [{"id": "a", "equipo": "A"},
                                  {"id": "b", "equipo": "B"}]}

    async def async_verify_group_season(self, ids):
        self.calls.append("verify")
        assert ids == ["a", "b"]
        return {"season_verified": bool(self.season), "season_id": self.season}


class CompetitionManagerTests(unittest.TestCase):
    def test_two_team_verified_selection_and_group_key(self):
        client = OfficialTeamClient()
        result = asyncio.run(mod.identify_competition(client, "a"))
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["team_count"], 2)
        self.assertEqual(mod.group_selection(result), {
            "season_id": "official-season", "phase_id": "f",
            "group_id": "g", "season_verified": True})
        self.assertEqual(client.calls, ["identity", "standings", "verify"])

    def test_group_metadata_cannot_bypass_independent_season_check(self):
        client = OfficialTeamClient(season=None)
        async def misleading_identity(team_id):
            client.calls.append("identity")
            return {"season_verified": True, "season_id": "unproven-season",
                    "phase_id": "f", "group_id": "g"}
        client.async_team_group_identity = misleading_identity
        result = asyncio.run(mod.identify_competition(client, "a"))
        self.assertEqual(result["status"], "season_unverified")
        self.assertEqual(client.calls, ["identity", "standings", "verify"])

    def test_diagnostic_only_returns_flags_not_private_ids(self):
        success = asyncio.run(
            mod.competition_season_diagnostic(OfficialTeamClient(), "a"))
        self.assertEqual(success, {
            "status": "verified", "group_verified": True,
            "team_count": 2, "season_match_verified": True})
        self.assertNotIn("official-season", repr(success))
        missing = asyncio.run(mod.competition_season_diagnostic(
            OfficialTeamClient(season=None), "a"))
        self.assertFalse(missing["season_match_verified"])
        self.assertNotIn("season_id", missing)

    def test_no_follow_without_official_season(self):
        result = asyncio.run(mod.identify_competition(OfficialTeamClient(season=None), "a"))
        self.assertEqual(result["status"], "season_unverified")
        with self.assertRaises(ValueError):
            mod.group_selection(result)

    def test_rejects_team_not_present_in_group(self):
        client = OfficialTeamClient()
        with self.assertRaises(ValueError):
            asyncio.run(mod.identify_competition(client, "another-team"))
        self.assertEqual(client.calls, ["identity", "standings"])

    def test_bad_team_id_cannot_trigger_requests(self):
        client = OfficialTeamClient()
        for item in ("", "  ", "X" * 513, None):
            with self.subTest(item=repr(item)), self.assertRaises(ValueError):
                asyncio.run(mod.identify_competition(client, item))
        self.assertEqual(client.calls, [])

    def test_fails_closed_on_duplicate_opponents(self):
        client = OfficialTeamClient()
        async def bad_standings(team_id):
            return {"clasificacion": [{"id": "a"}, {"id": "a"}]}
        client.async_team_standings = bad_standings
        with self.assertRaises(ValueError):
            asyncio.run(mod.identify_competition(client, "a"))
        self.assertNotIn("verify", client.calls)


if __name__ == "__main__":
    unittest.main()
