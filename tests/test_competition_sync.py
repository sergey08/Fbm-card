"""Offline tests for FBM competition archive and group synchronization."""
import asyncio
from datetime import date
import importlib.util
from pathlib import Path
import tempfile
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

Archive = module("competition_archive").CompetitionArchive
sync_group = module("competition_sync").sync_group
preview_group = module("competition_sync").preview_group


def identity(verified=True):
    return {"season_id": "2026-27", "phase_id": "phase1",
            "group_id": "group1", "season_verified": verified}


class FakeClient:
    def __init__(self, verified=True):
        self.verified = verified
        self.calls = []

    async def async_team_group_identity(self, team):
        self.calls.append(("identity", team))
        return identity(self.verified)

    async def async_verify_group_season(self, team_ids):
        self.calls.append(("verify_season", tuple(team_ids)))
        return {"season_verified": self.verified,
                "season_id": "2026-27" if self.verified else None,
                "season_evidence_status": "two_team_official_detail"
                    if self.verified else "unverified_player_binding"}

    async def async_team_standings(self, team):
        self.calls.append(("standings", team))
        return {"clasificacion": [{"id": "a", "equipo": "A"},
                                  {"id": "b", "equipo": "B"}]}

    async def async_team_schedule(self, team, start, end):
        self.calls.append(("schedule", team))
        return {"partidos": [{"id": "m1", "local": "A", "visitante": "B"}]}

    async def async_team_roster(self, team):
        self.calls.append(("roster", team))
        return {"jugadores": [{"id": team + "-p1", "nombre": "Ejemplo",
                               "puntos_totales": 5, "foto": "private-photo"}]}


class CompetitionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Archive(str(Path(tmp.name) / "competition.sqlite"))

    def test_requires_verified_season(self):
        with self.assertRaises(ValueError):
            self.store.follow(identity(False))
        client = FakeClient(verified=False)
        result = asyncio.run(sync_group(client, self.store, "a",
                                       date(2026, 10, 1), date(2026, 11, 1)))
        self.assertEqual(result["status"], "season_unverified")
        self.assertEqual(client.calls, [("identity", "a"), ("standings", "a"), ("verify_season", ("a", "b"))])
        self.assertEqual(self.store.followed(), [])

    def test_sync_does_not_trust_group_flag_without_cross_check(self):
        client = FakeClient(verified=True)
        async def unverified(teams):
            client.calls.append(("verify_season", tuple(teams)))
            return {"season_verified": False,
                    "season_evidence_status": "conflicting"}
        client.async_verify_group_season = unverified
        self.store.follow(identity())
        result = asyncio.run(sync_group(
            client, self.store, "a", date(2026, 10, 1), date(2026, 11, 1)))
        self.assertEqual(result["status"], "season_unverified")
        self.assertFalse(result["saved"])
        self.assertIn(("verify_season", ("a", "b")), client.calls)
        self.assertFalse(any(kind in ("schedule", "roster")
                             for kind, _ in client.calls))
        self.assertIsNone(self.store.latest(identity(), "fixtures"))

    def test_preview_reads_group_without_players_or_storage(self):
        client = FakeClient(verified=False)
        result = asyncio.run(preview_group(client, "a",
                                           date(2026, 10, 1), date(2026, 11, 1)))
        self.assertEqual(result["status"], "preview")
        self.assertFalse(result["persisted"])
        self.assertFalse(result["season_verified"])
        self.assertEqual(result["team_count"], 2)
        self.assertEqual(result["match_count"], 1)
        self.assertEqual(len(client.calls), 3)
        self.assertFalse(any(kind == "roster" for kind, _ in client.calls))
        self.assertEqual(self.store.followed(), [])

    def test_official_two_team_season_verification_allows_archive(self):
        client = FakeClient(verified=False)
        original = client.async_verify_group_season
        async def confirm(team_ids):
            self.assertEqual(team_ids, ["a", "b"])
            return {"season_verified": True, "season_id": "official-season",
                    "season_evidence_status": "two_team_official_detail"}
        client.async_verify_group_season = confirm
        self.store.follow({"season_verified": True, "season_id": "official-season",
                           "phase_id": "phase1", "group_id": "group1"})
        result = asyncio.run(sync_group(client, self.store, "a",
                                        date(2026,10,1), date(2026,11,1),
                                        fetch_rosters=False))
        self.assertTrue(result["saved"])
        self.assertEqual(result["competition"]["season_id"], "official-season")
        self.assertEqual(len(self.store.followed()), 1)

    def test_rejects_selected_team_not_listed_in_group(self):
        client = FakeClient(verified=False)
        with self.assertRaises(ValueError):
            asyncio.run(sync_group(client, self.store, "not-a-member",
                                   date(2026,10,1), date(2026,11,1)))
        self.assertFalse(any(kind == "verify_season" for kind, _ in client.calls))

    def test_full_group_deduped_and_photos_removed(self):
        client = FakeClient()
        self.store.follow(identity())
        async def sync():
            return await sync_group(client, self.store, "a",
                                    date(2026, 10, 1), date(2026, 11, 1))
        report = asyncio.run(sync())
        self.assertEqual(report["team_count"], 2)
        self.assertEqual(report["rosters_saved"], 2)
        self.assertEqual(report["fixture_count"], 1)
        self.assertEqual(len(self.store.followed()), 1)
        saved = self.store.latest(identity(), "roster", "a")["payload"]
        self.assertEqual(saved["jugadores"][0]["puntos_totales"], 5)
        self.assertNotIn("foto", saved["jugadores"][0])
        self.assertNotIn("private-photo", str(saved))
        reopened = Archive(self.store.path)
        self.assertEqual(reopened.latest(identity(), "fixtures")["payload"]["partidos"][0]["id"], "m1")

    def test_changed_competition_aborts_before_fixture_and_roster_fetch(self):
        client = FakeClient()
        self.store.follow(identity())
        wanted = {"season_id": "2026-27", "phase_id": "phase1",
                  "group_id": "group-other"}
        result = asyncio.run(sync_group(
            client, self.store, "a", date(2026, 10, 1),
            date(2026, 11, 1), expected_competition=wanted))
        self.assertEqual(result["status"], "competition_changed")
        self.assertFalse(result["saved"])
        self.assertFalse(any(action in ("schedule", "roster")
                             for action, _ in client.calls))
        self.assertIsNone(self.store.latest(identity(), "fixtures"))

    def test_stop_following_during_roster_fetch_prevents_further_requests(self):
        self.store.follow(identity())
        store = self.store
        class RevokingClient(FakeClient):
            async def async_team_roster(self, team):
                result = await super().async_team_roster(team)
                store.unfollow(identity())
                return result
        client = RevokingClient()
        result = asyncio.run(sync_group(client, store, "a",
                                        date(2026, 10, 1), date(2026, 11, 1)))
        self.assertEqual(result["status"], "not_followed")
        self.assertFalse(result["saved"])
        self.assertEqual(sum(kind == "roster" for kind, _ in client.calls), 1)
        self.assertIsNone(store.latest(identity(), "fixtures"))
        self.assertIsNone(store.latest(identity(), "roster", "a"))

    def test_idempotent_refresh_is_not_reported_as_failure(self):
        self.store.follow(identity())
        client = FakeClient()
        async def twice():
            first = await sync_group(client, self.store, "a",
                                     date(2026, 10, 1), date(2026, 11, 1),
                                     fetch_rosters=False)
            second = await sync_group(client, self.store, "a",
                                      date(2026, 10, 1), date(2026, 11, 1),
                                      fetch_rosters=False)
            return first, second
        first, second = asyncio.run(twice())
        self.assertEqual(first["status"], "ok")
        self.assertEqual(second["status"], "ok")
        self.assertTrue(second["saved"])
        self.assertEqual(second["records_written"], 0)

    def test_unselected_competition_cannot_download_or_save_rosters(self):
        client = FakeClient()
        result = asyncio.run(sync_group(client, self.store, "a",
                                        date(2026, 10, 1), date(2026, 11, 1)))
        self.assertEqual(result["status"], "not_followed")
        self.assertFalse(result["saved"])
        self.assertFalse(any(action in ("roster", "schedule")
                             for action, _ in client.calls))
        self.assertEqual(self.store.followed(), [])

    def test_anchor_is_persisted_and_deduplicated(self):
        selection = identity()
        self.store.follow(selection, "team-A")
        self.store.follow(selection, "team-B")
        self.assertEqual(len(self.store.followed()), 1)
        self.assertEqual(
            self.store.followed_with_anchor()[0]["anchor_team_id"], "team-B"
        )
        self.store.follow(selection)
        self.assertEqual(
            self.store.followed_with_anchor()[0]["anchor_team_id"], "team-B"
        )
        self.store.unfollow(selection)
        self.assertFalse(self.store.is_followed(selection))
        self.assertEqual(self.store.followed_with_anchor(), [])

    def test_legacy_competition_schema_is_migrated_without_losing_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbpath = str(Path(tmp) / "old.db")
            with sqlite3.connect(dbpath) as db:
                db.execute("""CREATE TABLE competitions(
                    season TEXT NOT NULL, phase TEXT NOT NULL,
                    group_id TEXT NOT NULL, followed INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (season,phase,group_id))""")
                db.execute("INSERT INTO competitions VALUES ('old','phase','group',1)")
            archived = Archive(dbpath)
            self.assertEqual(archived.followed_with_anchor(), [
                {"season_id": "old", "phase_id": "phase",
                 "group_id": "group", "anchor_team_id": ""}
            ])
            with sqlite3.connect(dbpath) as db:
                self.assertEqual(db.execute("SELECT followed FROM competitions").fetchone()[0], 1)

    def test_images_and_unknown_fields_never_enter_archive(self):
        self.store.follow(identity())
        fixtures = {"partidos": [{"id": "p", "local": "Local",
            "visitante": "Visitante", "img_local": "PRIVATE-IMAGE",
            "escudo_visitante": "PRIVATE-CREST", "estado": "finished",
            "marcador": {"local": 3, "visitante": 2}}]}
        self.assertTrue(self.store.record(identity(), "fixtures", fixtures))
        clean = self.store.latest(identity(), "fixtures")["payload"]
        self.assertNotIn("PRIVATE", str(clean))
        self.assertEqual(clean["partidos"][0]["marcador"]["local"], 3)
        standings = {"clasificacion": [{"id": "a", "equipo": "Equipo",
            "escudo": "PRIVATE-CREST", "ganados": 5}]}
        self.assertTrue(self.store.record(identity(), "standings", standings))
        self.assertNotIn("PRIVATE", str(self.store.latest(identity(), "standings")))
        
    def test_stale_records_and_identity_separation(self):
        self.store.follow(identity())
        self.assertTrue(self.store.record(identity(), "standings", {"clasificacion": []},
                                          observed_at="2026-11-10T12:00:00Z"))
        self.assertFalse(self.store.record(identity(), "standings", {"clasificacion": []},
                                           observed_at="2026-11-09T12:00:00Z"))
        self.assertFalse(self.store.record(identity(), "standings", {"clasificacion": []},
                                           observed_at="2026-11-11T12:00:00Z"))  # sin cambios
        other = {**identity(), "group_id": "group2"}
        self.assertIsNone(self.store.latest(other, "standings"))
        with self.assertRaises(ValueError):
            self.store.record(identity(), "unknown", {})
        self.store.unfollow(identity())
        self.assertFalse(self.store.record(identity(), "fixtures", {"partidos": []}))

    def test_reject_oversized_or_invalid_inputs(self):
        self.store.follow(identity())
        with self.assertRaises(ValueError):
            self.store.record(identity(), "roster", {"jugadores": []}, subject="")
        with self.assertRaises(ValueError):
            self.store.record(identity(), "standings", {"clasificacion": "not a list"})
        with self.assertRaises(ValueError):
            self.store.record(identity(), "roster", {"jugadores": [
                {"nombre": "x" * 2000000}]}, subject="a")


if __name__ == "__main__":
    unittest.main()
