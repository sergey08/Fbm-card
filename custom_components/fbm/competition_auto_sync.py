"""Opt-in, restart-safe scheduled FBM refresh.

Native HA event listeners only; never run unless options opt in.
Each tick performs at most one followed group or one five-player batch.
Only public team data is visible in the regular HA sensor.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .competition_sync import sync_group
from .competition_player_stats import sync_player_stats_batch

GROUP_INTERVAL = timedelta(hours=4)
PLAYER_INTERVAL = timedelta(hours=2)
PLAYER_CYCLE_DELAY = timedelta(hours=24)


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
        self.health = {"groups": {"status": "pending", "last_run": None},
                       "players": {"status": "pending", "last_run": None}}

    def _mark(self, kind, status):
        # Safe, in-memory diagnostics: never expose players or API payloads.
        self.health[kind] = {"status": status,
                             "last_run": datetime.now(timezone.utc).isoformat()}

    async def async_start(self, groups: bool, players: bool):
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

    def _group_tick(self, _now):
        if not self._stopped and not self._group_lock.locked():
            self._spawn(self._run_group())

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
            archive, groups = await self._archive_and_groups()
            if not groups:
                self._mark("groups", "no_followed_groups")
                return
            state = await self._read_state()
            index = int(state.get("group_index", 0)) % len(groups)
            group = groups[index]
            # Advance even after a network failure so one group does not
            # permanently block others. Never follow automatically.
            await self._save_state({"group_index": (index + 1) % len(groups)})
            if self._stopped:
                return
            now = date.today()
            try:
                response = await sync_group(
                    self.client, archive, group["anchor_team_id"],
                    now - timedelta(days=45), now + timedelta(days=60),
                    fetch_rosters=False,
                    expected_competition={k: group[k] for k in
                                          ("season_id", "phase_id", "group_id")})
                self._mark("groups", "ok" if response.get("status") == "ok" else "failed")
            except (OSError, ValueError, RuntimeError):
                # Keep last-good archived snapshot. No auto-enrollment.
                self._mark("groups", "failed")
                return

    async def _run_players(self):
        async with self._player_lock:
            if self._stopped:
                return
            archive, groups = await self._archive_and_groups()
            if not groups:
                self._mark("players", "no_followed_groups")
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
                self._mark("players", "no_standings")
                return
            team_index = int(cursor.get("team_index", 0)) % len(team_ids)
            offset = max(0, int(cursor.get("offset", 0)))
            if self._stopped:
                return
            response = await sync_player_stats_batch(
                self.client, archive, identity, team_ids[team_index],
                offset=offset, limit=5)
            if response.get("status") not in ("ok", "partial", "no_roster"):
                self._mark("players", "failed")
                return
            if response.get("next_offset") is not None:
                cursor = {"group_index": group_index,
                          "team_index": team_index,
                          "offset": response["next_offset"]}
            elif team_index + 1 < len(team_ids):
                cursor = {"group_index": group_index,
                          "team_index": team_index + 1, "offset": 0}
            elif group_index + 1 < len(groups):
                cursor = {"group_index": group_index + 1,
                          "team_index": 0, "offset": 0}
            else:
                cursor = {"group_index": 0, "team_index": 0, "offset": 0,
                          "cycle_finished_at": datetime.now(timezone.utc).isoformat()}
            await self._save_state({"players": cursor})
            self._mark("players", response["status"])
