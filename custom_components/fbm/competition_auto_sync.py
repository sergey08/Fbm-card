"""Opt-in, restart-safe scheduled FBM refresh.

Native HA event listeners only; never run unless options opt in.
Each tick performs at most one followed group or one five-player batch.
Only public team data is visible in the regular HA sensor.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .competition_sync import sync_group
from .competition_player_stats import sync_player_stats_batch
from .competition_refresh_policy import should_poll_group

GROUP_INTERVAL = timedelta(hours=1)
PLAYER_INTERVAL = timedelta(minutes=30)
PLAYER_CYCLE_DELAY = timedelta(hours=24)
PLAYER_FULL_RECHECK_INTERVAL = timedelta(days=7)
ROSTER_FULL_RECHECK_INTERVAL = timedelta(days=7)


class CompetitionAutoUpdater:
    def __init__(self, hass, entry_id: str, client, archive_path, archive_factory):
        self.hass = hass
        self.entry_id = entry_id
        self.client = client
        self.archive_path = archive_path
        self.archive_factory = archive_factory
        self.storage = Store(hass, 1, f"fbm_auto_sync_{entry_id}", private=True,
                             atomic_writes=True)
        self._cancel = []
        self._tasks = set()
        self._stopped = False
        self._group_lock = asyncio.Lock()
        self._player_lock = asyncio.Lock()
        self._store_lock = asyncio.Lock()
        self.group_checked_at = {}
        self.health = {"groups": {"status": "pending", "last_run": None},
                       "players": {"status": "pending", "last_run": None}}

    async def _mark(self, kind, status, metrics=None):
        # Persist only bounded numeric counters, never names, player IDs,
        # error messages, match details or raw FBM responses.
        record = {"status": status,
                  "last_run": datetime.now(timezone.utc).isoformat()}
        if kind == "players" and type(metrics) is dict:
            for key in ("processed", "saved", "skipped_unchanged",
                        "errors", "players_without_match_data",
                        "retry_pending"):
                value = metrics.get(key)
                if type(value) is int and 0 <= value <= 100:
                    record[key] = value
        self.health[kind] = record
        try:
            await self._save_state({"health": {kind: record}})
        except Exception:
            # Storage failure must not suppress live HA diagnostics or
            # interfere with already archived competition snapshots.
            pass
        async_dispatcher_send(self.hass, f"fbm_competitions_refresh_{self.entry_id}")

    async def async_start(self, groups: bool, players: bool):
        # Restore diagnostics independently of work cursors after a restart.
        try:
            snapshot = await self._read_state()
            saved = snapshot.get("health", {})
            checks = snapshot.get("group_checked_at", {})
            if type(checks) is dict:
                self.group_checked_at = {k: v for k, v in checks.items()
                    if type(k) is str and 0 < len(k) <= 512
                    and type(v) is str and len(v) < 64}
            if type(saved) is dict:
                for kind in ("groups", "players"):
                    record = saved.get(kind)
                    if (type(record) is dict
                            and record.get("status") in
                            ("ok", "partial", "failed", "no_followed_groups", "no_standings", "no_roster")
                            and type(record.get("last_run")) is str
                            and len(record["last_run"]) < 64):
                        try:
                            stamp = datetime.fromisoformat(record["last_run"])
                        except ValueError:
                            continue
                        if stamp.tzinfo is not None:
                            self.health[kind] = {
                                "status": record["status"],
                                "last_run": record["last_run"]}
                            if kind == "players":
                                for key in ("processed", "saved",
                                            "skipped_unchanged", "errors",
                                            "players_without_match_data",
                                            "retry_pending"):
                                    value = record.get(key)
                                    if type(value) is int and 0 <= value <= 100:
                                        self.health[kind][key] = value
        except Exception:
            # A broken state store should not prevent the scheduler starting.
            pass
        if groups:
            self._cancel.append(async_track_time_interval(
                self.hass, self._group_tick, GROUP_INTERVAL))
        if players:
            self._cancel.append(async_track_time_interval(
                self.hass, self._player_tick, PLAYER_INTERVAL))

    async def async_stop(self):
        self._stopped = True
        for cancel in self._cancel:
            cancel()
        self._cancel.clear()
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    @callback
    def _group_tick(self, _now):
        if not self._stopped and not self._group_lock.locked():
            self._spawn(self._run_group())

    @callback
    def _player_tick(self, _now):
        if not self._stopped and not self._player_lock.locked():
            self._spawn(self._run_players())

    def _spawn(self, coro):
        task = self.hass.async_create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _read_state(self):
        state = await self.storage.async_load()
        return state if type(state) is dict else {}

    async def _save_state(self, state):
        # Read/merge per-workstream cursor so concurrent timers cannot
        # overwrite one another's state in Home Assistant's Store.
        async with self._store_lock:
            current = await self._read_state()
            # Preserve both workstream health records when their timers overlap.
            if "health" in state:
                previous = current.get("health", {})
                if type(previous) is not dict:
                    previous = {}
                current["health"] = {**previous, **state["health"]}
                state = {key: val for key, val in state.items() if key != "health"}
            current.update(state)
            await self.storage.async_save(current)

    async def _archive_and_groups(self):
        # Do not create DB when there is no followed group; all source
        # names come from the explicit native selection flow.
        from pathlib import Path
        if not await self.hass.async_add_executor_job(
                Path(self.archive_path).is_file):
            return None, []
        archive = await self.hass.async_add_executor_job(
            self.archive_factory, self.archive_path)
        groups = await self.hass.async_add_executor_job(
            archive.followed_with_anchor)
        return archive, [g for g in groups if g.get("anchor_team_id")]

    async def _run_group(self):
        async with self._group_lock:
            if self._stopped:
                return
            try:
                await self._run_group_impl()
            except Exception:
                # Include archive/store errors, not just remote API failures.
                # Do not expose private FBM data in Home Assistant state.
                await self._mark("groups", "failed")

    async def _run_group_impl(self):
        if self._stopped:
            return
        archive, groups = await self._archive_and_groups()
        if not groups:
            await self._mark("groups", "no_followed_groups")
            return
        state = await self._read_state()
        index = int(state.get("group_index", 0)) % len(groups)
        group = groups[index]
        # Round-robin across every followed group, but do not poll FBM
        # outside the post-game window unless the weekly heartbeat is due.
        # Keep the last successful check in the private HA Store so an
        # unchanged SQLite snapshot does not cause repeated network calls.
        group_id = group["group_id"]
        checks = state.get("group_checked_at", {})
        if type(checks) is not dict:
            checks = {}
        previous = checks.get(group_id)
        identity = {**{k: group[k] for k in
                       ("season_id", "phase_id", "group_id")},
                    "season_verified": True}
        fixture_snapshot = await self.hass.async_add_executor_job(
            archive.latest, identity, "fixtures")
        if not should_poll_group(
                (fixture_snapshot or {}).get("payload"), previous,
                datetime.now(timezone.utc)):
            await self._save_state({"group_index": (index + 1) % len(groups)})
            return
        # Advance even after a network failure so one group does not
        # permanently block others. Never follow automatically.
        await self._save_state({"group_index": (index + 1) % len(groups)})
        if self._stopped:
            return
        # Refresh all official rosters at least weekly, even if no fixture
        # result changed. Newly registered players and corrections must not
        # remain hidden just because match scores are unchanged.
        roster_checks = state.get("roster_checked_at", {})
        if type(roster_checks) is not dict:
            roster_checks = {}
        last_roster = roster_checks.get(group_id)
        try:
            stamp = datetime.fromisoformat(last_roster) if type(last_roster) is str else None
            full_rosters_due = (stamp is None or stamp.tzinfo is None
                or datetime.now(timezone.utc) - stamp >= ROSTER_FULL_RECHECK_INTERVAL)
        except ValueError:
            full_rosters_due = True
        now = date.today()
        try:
            response = await sync_group(
                self.client, archive, group["anchor_team_id"],
                now - timedelta(days=45), now + timedelta(days=60),
                fetch_rosters=True if full_rosters_due else "on_change",
                expected_competition={k: group[k] for k in
                                      ("season_id", "phase_id", "group_id")})
            status = response.get("status") if isinstance(response, dict) else None
            if full_rosters_due and status == "ok":
                roster_checks = {k: v for k, v in roster_checks.items()
                                 if k in {item["group_id"] for item in groups}}
                roster_checks[group_id] = datetime.now(timezone.utc).isoformat()
                await self._save_state({"roster_checked_at": roster_checks})
            if status in ("ok", "partial"):
                # Bound Store metadata to current followed groups only.
                checks = {key: val for key, val in checks.items()
                          if key in {item["group_id"] for item in groups}}
                checks[group_id] = datetime.now(timezone.utc).isoformat()
                await self._save_state({"group_checked_at": checks})
                self.group_checked_at = checks
            await self._mark("groups", "ok" if status in ("ok", "partial") else "failed")
        except Exception:
            # Never leak service errors, IDs or player details into HA state.
            # The archive retains the last successful snapshot.
            await self._mark("groups", "failed")
            return

    async def _run_players(self):
        async with self._player_lock:
            if self._stopped:
                return
            try:
                await self._run_players_impl()
            except Exception:
                # FBM failures are contained and never disclose player data.
                await self._mark("players", "failed")

    async def _run_players_impl(self):
        archive, groups = await self._archive_and_groups()
        if not groups:
            await self._mark("players", "no_followed_groups")
            return
        state = await self._read_state()
        cursor = state.get("players", {})
        if type(cursor) is not dict:
            cursor = {}
        last = cursor.get("cycle_finished_at")
        if type(last) is str:
            try:
                completed = datetime.fromisoformat(last)
                if completed.tzinfo and datetime.now(timezone.utc) - completed < PLAYER_CYCLE_DELAY:
                    return
            except ValueError:
                pass
        group_index = int(cursor.get("group_index", 0)) % len(groups)
        selected = groups[group_index]
        identity = {**{k: selected[k] for k in
                      ("season_id", "phase_id", "group_id")},
                    "season_verified": True}
        # Only already archived rosters; no automatic mass enrollment.
        standing = await self.hass.async_add_executor_job(
            archive.latest, identity, "standings")
        rows = (standing or {}).get("payload", {}).get("clasificacion", [])
        team_ids = [row.get("id") for row in rows if type(row) is dict
                    and type(row.get("id")) is str][:20]
        if not team_ids:
            await self._mark("players", "no_standings")
            return
        team_index = int(cursor.get("team_index", 0)) % len(team_ids)
        offset = max(0, int(cursor.get("offset", 0)))
        starting_cycle = group_index == 0 and team_index == 0 and offset == 0
        if starting_cycle and "full_recheck" not in cursor:
            last_full = state.get("player_full_recheck_at")
            try:
                stamp = datetime.fromisoformat(last_full) if type(last_full) is str else None
                full_due = (stamp is None or stamp.tzinfo is None
                    or datetime.now(timezone.utc) - stamp >= PLAYER_FULL_RECHECK_INTERVAL)
            except ValueError:
                full_due = True
            cursor["full_recheck"] = full_due
        full_recheck = cursor.get("full_recheck") is True
        if self._stopped:
            return
        response = await sync_player_stats_batch(
            self.client, archive, identity, team_ids[team_index],
            offset=offset, limit=5, force_recheck=full_recheck)
        if response.get("status") not in ("ok", "partial", "no_roster"):
            await self._mark("players", "failed")
            return
        # Retry a partial batch once at the next scheduled tick. Keep
        # counters only: the private cursor contains no player identity.
        # The second failure advances as usual, so a bad official record
        # cannot block other teams or followed competitions indefinitely.
        attempt = int(cursor.get("retry_attempt", 0))
        should_retry = (
            response.get("status") == "partial"
            and type(response.get("errors")) is int
            and response["errors"] > 0
            and attempt == 0
        )
        if should_retry:
            await self._save_state({"players": {
                "group_index": group_index,
                "team_index": team_index,
                "offset": offset,
                "retry_attempt": 1, "full_recheck": full_recheck}})
            await self._mark("players", "partial", {
                **response, "retry_pending": 1})
            return
        if response.get("next_offset") is not None:
            cursor = {"group_index": group_index,
                      "team_index": team_index,
                      "offset": response["next_offset"], "full_recheck": full_recheck}
        elif team_index + 1 < len(team_ids):
            cursor = {"group_index": group_index,
                      "team_index": team_index + 1, "offset": 0,
                      "full_recheck": full_recheck}
        elif group_index + 1 < len(groups):
            cursor = {"group_index": group_index + 1,
                      "team_index": 0, "offset": 0,
                      "full_recheck": full_recheck}
        else:
            cursor = {"group_index": 0, "team_index": 0, "offset": 0,
                      "cycle_finished_at": datetime.now(timezone.utc).isoformat()}
        if "cycle_finished_at" in cursor and full_recheck:
            await self._save_state({
                "player_full_recheck_at": cursor["cycle_finished_at"]})
        # The bounded cursor advances across all followed groups; unchanged
        # player records are skipped by sync_player_stats_batch.  This lowers
        # the cost of a 30-minute pass while preserving the 5-player cap.
        await self._save_state({"players": cursor})
        await self._mark("players", response["status"], {
            **response, "retry_pending": 0})
