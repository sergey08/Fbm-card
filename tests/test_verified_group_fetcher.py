"""Fail-closed group bridge tests with a simulated official client."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock

p = Path(__file__).resolve().parents[1] / "custom_components/fbm/verified_group_fetcher.py"
spec = importlib.util.spec_from_file_location("verified_group_fetcher", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class BridgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = type("Client", (), {})()
        self.client.async_team_group_identity = AsyncMock(return_value={
            "source": "FBM", "season_verified": False, "season_id": None,
            "group_id": "g", "team_id": "t"})
        self.client.async_team_standings = AsyncMock(return_value={"clasificacion": []})
        self.bridge = mod.VerifiedGroupFetcher(self.client, {("s", "g"): "t"})

    async def test_current_official_contract_blocks_sync_before_standings(self):
        with self.assertRaises(mod.UnverifiedGroupIdentity):
            await self.bridge("s", "g")
        self.client.async_team_group_identity.assert_awaited_once_with("t")
        self.client.async_team_standings.assert_not_awaited()

    async def test_missing_explicit_team_blocks_all_traffic(self):
        with self.assertRaises(mod.UnverifiedGroupIdentity):
            await self.bridge("s", "another")
        self.client.async_team_group_identity.assert_not_awaited()

    async def test_wrong_group_or_season_rejected(self):
        for changed in ({"season_verified": True, "season_id": "other"},
                        {"season_verified": True, "season_id": "s", "group_id": "other"}):
            self.client.async_team_group_identity.return_value = {
                "source": "FBM", "team_id": "t", "group_id": "g",
                "season_id": "s", **changed}
            with self.assertRaises(mod.UnverifiedGroupIdentity):
                await self.bridge("s", "g")
        self.client.async_team_standings.assert_not_awaited()

    async def test_verified_matching_binding_allows_normalized_standings(self):
        self.client.async_team_group_identity.return_value = {
            "source": "FBM", "season_verified": True,
            "season_id": "s", "group_id": "g", "team_id": "t"}
        result = await self.bridge("s", "g")
        self.assertEqual(result, {"clasificacion": []})
        self.client.async_team_standings.assert_awaited_once_with("t")

    async def test_no_unverified_source(self):
        self.client.async_team_group_identity.return_value = {
            "source": "other", "season_verified": True,
            "season_id": "s", "group_id": "g", "team_id": "t"}
        with self.assertRaises(mod.UnverifiedGroupIdentity):
            await self.bridge("s", "g")
        self.client.async_team_standings.assert_not_awaited()

if __name__ == "__main__":
    unittest.main()
