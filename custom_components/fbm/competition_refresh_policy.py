"""Conservative schedule-aware polling for followed FBM groups.

This module is pure and never calls external services. Poll around known game
dates, once after a restart/initial subscription, or at least once per week to
catch reschedules and unexpected source corrections.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


FBM_TIMEZONE = ZoneInfo("Europe/Madrid")
PENDING_SCORE_INTERVAL = timedelta(minutes=30)


def should_poll_group(fixtures: dict | None, last_checked: str | None,
                      now: datetime) -> bool:
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Timezone-aware instant required")
    if not last_checked:
        return True
    try:
        previous = datetime.fromisoformat(last_checked)
    except (TypeError, ValueError):
        return True
    if previous.tzinfo is None or previous > now:
        return True
    age = now - previous
    if age >= timedelta(days=7):
        return True
    if age < PENDING_SCORE_INTERVAL:
        return False
    rows = fixtures.get("partidos") if isinstance(fixtures, dict) else None
    if not isinstance(rows, list) or len(rows) > 2000:
        return age >= timedelta(hours=4)
    today = now.astimezone(FBM_TIMEZONE).date()
    near_game = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("fecha")
        if not isinstance(value, str):
            continue
        try:
            day = datetime.strptime(value, "%d/%m/%Y").date()
        except ValueError:
            try:
                day = date.fromisoformat(value)
            except ValueError:
                continue
        days = (day - today).days
        near_game |= -2 <= days <= 2
        if (-2 <= days <= 0 and row.get("marcador") is None
                and row.get("estado") in {"scheduled", "unknown", "live"}):
            return True
    return near_game and age >= timedelta(hours=4)
