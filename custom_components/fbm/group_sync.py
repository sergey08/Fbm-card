"""DEV-only coordinator for explicitly followed, verified FBM groups.

No background scheduling is started by importing this module. The caller must
resolve an official season/group pair and supply a trusted classification fetcher.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable


class GroupSyncCoordinator:
    """Opt-in classification synchronization with per-group status.

    fetch_classification(season, group_id) must return a verified, normalized
    classification from the official FBM adapter. Do not pass search results
    or unverified calendar/player payloads as this callback.
    """

    def __init__(self, store, fetch_classification: Callable[..., Awaitable[dict]],
                 *, weekday_minutes: int = 180, weekend_minutes: int = 30):
        for value in (weekday_minutes, weekend_minutes):
            if type(value) is not int or not 5 <= value <= 1440:
                raise ValueError("Intervalos entre 5 y 1440 minutos")
        self.store = store
        self.fetch = fetch_classification
        self.weekday_minutes = weekday_minutes
        self.weekend_minutes = weekend_minutes
        self._locks = {}
        self._status = {}

    def _interval(self, now: datetime) -> timedelta:
        minutes = self.weekend_minutes if now.weekday() >= 5 else self.weekday_minutes
        return timedelta(minutes=minutes)

    @staticmethod
    def _now(now):
        now = now or datetime.now(timezone.utc)
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("Se requiere fecha con zona horaria")
        return now.astimezone(timezone.utc)

    def due(self, season: str, group_id: str, *, now=None) -> bool:
        """Only followed groups can be due. Failures use interval backoff."""
        now = self._now(now)
        if (season, group_id) not in self.store.followed():
            return False
        state = self._status.get((season, group_id))
        if state and state.get("last_attempt"):
            last = datetime.fromisoformat(state["last_attempt"])
            if now < last + self._interval(now):
                return False
        snapshot = self.store.latest(season, group_id)
        if snapshot and not state:
            try:
                last = datetime.fromisoformat(snapshot["observed_at"])
                if now < last + self._interval(now):
                    return False
            except (ValueError, TypeError):
                return False
        return True

    async def refresh(self, season: str, group_id: str, *, now=None, manual=False) -> dict:
        now = self._now(now)
        # Validate input before any lookup or network call.
        season, group_id = self.store._key(season, group_id)
        key = (season, group_id)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if key not in self.store.followed():
                return self.summary(season, group_id, status_override="not_followed")
            if not manual and not self.due(season, group_id, now=now):
                return self.summary(season, group_id)
            status = self._status.setdefault(key, {})
            status["last_attempt"] = now.isoformat()
            try:
                payload = await self.fetch(season, group_id)
                # Recheck after request, so unfollow during network IO wins.
                if key not in self.store.followed():
                    return self.summary(season, group_id, status_override="not_followed")
                stored = self.store.record(season, group_id, "clasificacion", payload,
                                           observed_at=now.isoformat())
                status["status"] = "ok" if stored else "unchanged"
                if stored:
                    status["last_success"] = now.isoformat()
                status.pop("error", None)
            except Exception:
                # Do not expose tokens, requests, or private exception content.
                status["status"] = "error"
                status["error"] = "No se pudo actualizar la clasificación oficial"
            return self.summary(season, group_id)

    def summary(self, season: str, group_id: str, *, status_override=None) -> dict:
        season, group_id = self.store._key(season, group_id)
        followed = (season, group_id) in self.store.followed()
        snapshot = self.store.latest(season, group_id)
        status = self._status.get((season, group_id), {})
        return {
            "season": season,
            "group_id": group_id,
            "followed": followed,
            "status": status_override or ("not_followed" if not followed else status.get("status", "pending")),
            "last_attempt": status.get("last_attempt"),
            "last_success": snapshot["observed_at"] if snapshot else None,
            "classification_available": snapshot is not None,
            "source_status": {"clasificacion": "available" if snapshot else "pending",
                              "calendario": "unverified", "jugadores": "unverified",
                              "estadisticas": "unverified"},
        }

    async def refresh_due(self, *, now=None) -> list[dict]:
        """Explicit tick only; HA integration must schedule this separately."""
        now = self._now(now)
        results = []
        for season, group_id in self.store.followed():
            if self.due(season, group_id, now=now):
                results.append(await self.refresh(season, group_id, now=now))
        return results
