"""Offline checks for opt-in HA scheduler, persisted cursors and clean unload."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT=Path(__file__).resolve().parents[1]/"custom_components"/"fbm"
PKG="test_competition_auto_package"
pkg=types.ModuleType(PKG)
pkg.__path__=[str(ROOT)]
sys.modules[PKG]=pkg

core_name="homeassistant.core"
core_mod=sys.modules.setdefault(core_name,types.ModuleType(core_name))
def callback(fn):
    fn.__ha_callback=True
    return fn
core_mod.callback=callback

event_name="homeassistant.helpers.event"
event_mod=sys.modules.setdefault(event_name,types.ModuleType(event_name))
listeners=[]
def track(hass, callback, interval):
    record={"callback":callback,"interval":interval,"cancelled":False}
    listeners.append(record)
    def cancel():
        record["cancelled"]=True
    return cancel
event_mod.async_track_time_interval=track

dispatcher_name="homeassistant.helpers.dispatcher"
dispatcher_mod=sys.modules.setdefault(dispatcher_name,types.ModuleType(dispatcher_name))
dispatched=[]
def send(hass, signal):
    dispatched.append(signal)
dispatcher_mod.async_dispatcher_send=send

store_name="homeassistant.helpers.storage"
store_mod=sys.modules.setdefault(store_name,types.ModuleType(store_name))
stored={}
class Store:
    def __init__(self,hass,version,key,**kwargs):
        self.key=key
    async def async_load(self):
        return stored.get(self.key)
    async def async_save(self,value):
        stored[self.key]=dict(value)
store_mod.Store=Store

def import_part(name):
    spec=importlib.util.spec_from_file_location(
        PKG+"."+name,ROOT/(name+".py"))
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

Archive=import_part("competition_archive").CompetitionArchive
import_part("competition_sync")
import_part("competition_player_stats")
mod=import_part("competition_auto_sync")
IDENT={"season_verified":True,"season_id":"26/27",
       "phase_id":"phase","group_id":"group"}

class Hass:
    async def async_add_executor_job(self,fn,*args):
        return fn(*args)
    def async_create_task(self,coro):
        return asyncio.create_task(coro)

class FakeClient:
    pass

class AutoTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        listeners.clear()
        stored.clear()
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=str(Path(self.temp.name)/"comp.sqlite")
        archive=Archive(self.path)
        archive.follow(IDENT,"anchor")
        archive.record(IDENT,"standings",{"clasificacion":[
            {"id":"a","equipo":"A"},{"id":"b","equipo":"B"}]})
        self.hass=Hass()
        self.updater=mod.CompetitionAutoUpdater(
            self.hass,"test",FakeClient(),self.path,Archive)

    async def test_mark_notifies_competition_sensor(self):
        await self.updater._mark("groups", "ok")
        self.assertEqual(dispatched[-1], "fbm_competitions_refresh_test")
        self.assertEqual(self.updater.health["groups"]["status"], "ok")
        self.assertIsNotNone(self.updater.health["groups"]["last_run"])

    async def test_health_survives_restart_without_replaying_tasks(self):
        await self.updater._mark("players", "ok")
        last = self.updater.health["players"]["last_run"]
        restarted = mod.CompetitionAutoUpdater(
            self.hass, "test", FakeClient(), self.path, Archive)
        self.assertIsNone(restarted.health["players"]["last_run"])
        await restarted.async_start(True, True)
        self.assertEqual(restarted.health["players"],
                         {"status": "ok", "last_run": last})
        self.assertEqual(restarted.health["groups"]["status"], "pending")
        self.assertEqual(len(listeners), 2)
        await restarted.async_stop()

    async def test_each_followed_group_restores_last_checked(self):
        from datetime import datetime, timedelta, timezone
        self.assertEqual(self.updater.group_checked_at, {})
        archive = Archive(self.path)
        archive.record(IDENT, "fixtures", {"partidos": [
            {"id": "future", "fecha": "31/12/2040",
             "estado": "scheduled", "local": "A", "visitante": "B"}
        ]})
        with patch.object(mod, "sync_group", new_callable=AsyncMock) as sync:
            sync.return_value = {"status": "ok"}
            await self.updater._run_group()
            self.assertEqual(sync.await_count, 1)
            self.assertIn("group", self.updater.group_checked_at)
            # The quiet-week policy must not query the same group again.
            await self.updater._run_group()
            self.assertEqual(sync.await_count, 1)
        restarted = mod.CompetitionAutoUpdater(
            self.hass, "test", FakeClient(), self.path, Archive)
        await restarted.async_start(True, True)
        self.assertEqual(restarted.group_checked_at,
                         self.updater.group_checked_at)
        await restarted.async_stop()

    async def test_group_and_player_health_merge_without_erasing_cursors(self):
        await self.updater._save_state({"players": {"offset": 5},
                                        "group_index": 1})
        await self.updater._mark("groups", "failed")
        await self.updater._mark("players", "ok")
        state = stored[self.updater.storage.key]
        self.assertEqual(state["group_index"], 1)
        self.assertEqual(state["players"]["offset"], 5)
        self.assertEqual(state["health"]["groups"]["status"], "failed")
        self.assertEqual(state["health"]["players"]["status"], "ok")

    async def test_invalid_persisted_health_not_restored(self):
        stored[self.updater.storage.key] = {"health": {
            "groups": {"status": "ok", "last_run": "invalid"},
            "players": {"status": "secret", "last_run": "2026-11-11T12:00:00+00:00"}}}
        await self.updater.async_start(True, True)
        self.assertEqual(self.updater.health["groups"]["status"], "pending")
        self.assertEqual(self.updater.health["players"]["status"], "pending")
        await self.updater.async_stop()

    async def test_repeated_identical_standings_do_not_duplicate_snapshots(self):
        archive=Archive(self.path)
        ranking={"clasificacion":[{"id":"a","equipo":"A"},{"id":"b","equipo":"B"}]}
        with sqlite3.connect(self.path) as db:
            before=db.execute(
                "SELECT COUNT(*) FROM snapshots WHERE source='standings'").fetchone()[0]
        # A later refresh with identical content must not create a new snapshot.
        written=archive.record(
            IDENT,"standings",ranking,
            observed_at="2099-01-01T00:00:00+00:00")
        with sqlite3.connect(self.path) as db:
            after=db.execute(
                "SELECT COUNT(*) FROM snapshots WHERE source='standings'").fetchone()[0]
        self.assertFalse(written)
        self.assertEqual(before,after)

    async def test_changed_standings_save_once_and_preserve_previous(self):
        archive=Archive(self.path)
        changed={"clasificacion":[
            {"id":"a","equipo":"A","puntos":8},
            {"id":"b","equipo":"B","puntos":6}]}
        first=archive.record(
            IDENT,"standings",changed,
            observed_at="2099-01-01T00:00:00+00:00")
        duplicate=archive.record(
            IDENT,"standings",changed,
            observed_at="2099-01-02T00:00:00+00:00")
        with sqlite3.connect(self.path) as db:
            snapshots=db.execute(
                "SELECT COUNT(*) FROM snapshots WHERE source='standings'").fetchone()[0]
        self.assertTrue(first)
        self.assertFalse(duplicate)
        self.assertEqual(snapshots,2)
        self.assertEqual(archive.latest(IDENT,"standings")["payload"],changed)

    async def test_bad_refresh_does_not_replace_last_good_snapshot(self):
        archive=Archive(self.path)
        good=archive.latest(IDENT,"standings")
        with self.assertRaises(ValueError):
            archive.record(
                IDENT,"standings",{"clasificacion":"invalid"},
                observed_at="2099-01-01T00:00:00+00:00")
        self.assertEqual(archive.latest(IDENT,"standings"),good)

    async def test_platform_initializes_after_automatic_flags(self):
        # Initial sensor poll must never observe the pre-options defaults.
        init_source=(ROOT/"__init__.py").read_text(encoding="utf-8")
        setup=init_source.split("async def async_setup_entry(",1)[1].split(
            "async def async_unload_entry(",1)[0]
        options_pos=setup.index('["auto_sync_flags"] = (')
        platform_pos=setup.index('async_forward_entry_setups(entry, ["sensor"])')
        self.assertLess(options_pos, platform_pos)
        self.assertLess(setup.index('await service.async_start('), platform_pos)

    async def test_disabled_does_not_register_timers_or_fetch(self):
        await self.updater.async_start(False,False)
        self.assertEqual(listeners,[])
        await self.updater.async_stop()

    async def test_enabled_registers_two_cancelable_native_timers(self):
        await self.updater.async_start(True,True)
        self.assertEqual(len(listeners),2)
        self.assertEqual(listeners[0]["interval"],mod.GROUP_INTERVAL)
        self.assertEqual(listeners[1]["interval"],mod.PLAYER_INTERVAL)
        await self.updater.async_stop()
        self.assertTrue(all(x["cancelled"] for x in listeners))

    async def test_time_interval_callbacks_are_marked_for_event_loop(self):
        # HA 2026.11 runs unmarked sync listeners in an executor thread;
        # hass.async_create_task must only run on the event loop.
        self.assertTrue(getattr(mod.CompetitionAutoUpdater._group_tick,
                                "__ha_callback", False))
        self.assertTrue(getattr(mod.CompetitionAutoUpdater._player_tick,
                                "__ha_callback", False))
        await self.updater.async_start(True,True)
        with patch.object(self.updater,"_run_group",new_callable=AsyncMock) as group:
            with patch.object(self.updater,"_run_players",new_callable=AsyncMock) as player:
                listeners[0]["callback"](None)
                listeners[1]["callback"](None)
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                group.assert_awaited_once()
                player.assert_awaited_once()
        await self.updater.async_stop()

    async def test_group_tick_targets_only_followed_group_without_roster(self):
        with patch.object(mod,"sync_group",new_callable=AsyncMock) as sync:
            await self.updater._run_group()
        sync.assert_awaited_once()
        self.assertEqual(sync.await_args.kwargs["fetch_rosters"], "on_change")
        self.assertEqual(sync.await_args.kwargs["expected_competition"]["season_id"],"26/27")
        self.assertEqual(stored[self.updater.storage.key]["group_index"],0)

    async def test_incremental_player_poll_keeps_five_player_cap(self):
        await self.updater.async_start(True, True)
        self.assertEqual(len(listeners), 2)
        self.assertEqual(listeners[1]["interval"], mod.timedelta(minutes=30))
        await self.updater.async_stop()

    async def test_stats_cursor_moves_and_survives_new_coordinator(self):
        with patch.object(mod,"sync_player_stats_batch",new_callable=AsyncMock) as sync:
            sync.return_value={"status":"ok","next_offset":5}
            await self.updater._run_players()
            self.assertEqual(sync.await_args.args[-1],"a")
            self.assertEqual(sync.await_args.kwargs["offset"],0)
            self.assertEqual(sync.await_args.kwargs["limit"],5)
            self.assertEqual(stored[self.updater.storage.key]["players"]["offset"],5)
            newer=mod.CompetitionAutoUpdater(
                self.hass,"test",FakeClient(),self.path,Archive)
            sync.return_value={"status":"ok","next_offset":None}
            await newer._run_players()
            self.assertEqual(sync.await_args.kwargs["offset"],5)
            self.assertEqual(stored[newer.storage.key]["players"]["team_index"],1)
        await newer.async_stop()

    async def test_scheduler_health_status_without_player_details(self):
        with patch.object(mod,"sync_group",new_callable=AsyncMock) as sync:
            sync.return_value={"status":"ok"}
            await self.updater._run_group()
        health=self.updater.health["groups"]
        self.assertEqual(health["status"],"ok")
        self.assertIsInstance(health["last_run"],str)
        self.assertNotIn("anchor",str(health))

    async def test_scheduler_group_failure_keeps_last_good_snapshot(self):
        with patch.object(mod,"sync_group",new_callable=AsyncMock) as sync:
            sync.side_effect=ValueError("hidden API details")
            await self.updater._run_group()
        self.assertEqual(self.updater.health["groups"]["status"],"failed")
        self.assertNotIn("hidden",str(self.updater.health))

    async def test_scheduler_player_health_is_bounded(self):
        with patch.object(mod,"sync_player_stats_batch",new_callable=AsyncMock) as sync:
            sync.return_value={"status":"ok","next_offset":5}
            await self.updater._run_players()
        self.assertEqual(self.updater.health["players"]["status"],"ok")
        self.assertNotIn("team_index",str(self.updater.health))

    async def test_unexpected_group_error_is_contained(self):
        with patch.object(mod,"sync_group",new_callable=AsyncMock) as sync:
            sync.side_effect=TypeError("private service failure")
            await self.updater._run_group()
        self.assertEqual(self.updater.health["groups"]["status"],"failed")
        self.assertNotIn("private",str(self.updater.health))

    async def test_unexpected_player_error_is_contained(self):
        with patch.object(mod,"sync_player_stats_batch",new_callable=AsyncMock) as sync:
            sync.side_effect=RuntimeError("private player details")
            await self.updater._run_players()
        self.assertEqual(self.updater.health["players"]["status"],"failed")
        self.assertNotIn("private",str(self.updater.health))

    async def test_group_archive_failure_is_contained(self):
        with patch.object(self.updater, "_archive_and_groups",
                          new_callable=AsyncMock) as load:
            load.side_effect=OSError("private archive path")
            await self.updater._run_group()
        self.assertEqual(self.updater.health["groups"]["status"], "failed")
        self.assertNotIn("private", str(self.updater.health))

    async def test_player_archive_failure_is_contained(self):
        with patch.object(self.updater, "_archive_and_groups",
                          new_callable=AsyncMock) as load:
            load.side_effect=OSError("private archive path")
            await self.updater._run_players()
        self.assertEqual(self.updater.health["players"]["status"], "failed")
        self.assertNotIn("private", str(self.updater.health))

    async def test_partial_group_refresh_is_not_reported_as_failure(self):
        with patch.object(mod,"sync_group",new_callable=AsyncMock) as sync:
            sync.return_value={"status":"partial"}
            await self.updater._run_group()
        self.assertEqual(self.updater.health["groups"]["status"],"ok")

    async def test_unfollow_blocks_group_and_player_requests(self):
        archive=Archive(self.path)
        archive.unfollow(IDENT)
        with patch.object(mod,"sync_group",new_callable=AsyncMock) as groups:
            with patch.object(mod,"sync_player_stats_batch",new_callable=AsyncMock) as players:
                await self.updater._run_group()
                await self.updater._run_players()
        groups.assert_not_awaited()
        players.assert_not_awaited()

if __name__=="__main__":
    unittest.main()
