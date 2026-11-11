"""Conservative schedule-aware polling for followed FBM groups.

This module is pure and never calls external services. Poll around known game
dates, once after a restart/initial subscription, or at least once per week to
catch reschedules and unexpected source corrections.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


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
    if age < timedelta(hours=4):
        return False
    rows = fixtures.get("partidos") if isinstance(fixtures, dict) else None
    if not isinstance(rows, list) or len(rows) > 2000:
        return True
    today = now.date()
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("fecha")
        if not isinstance(value, str):
            continue
        try:
            day = datetime.strptime(value, "%d/%m/%Y").date()
        except ValueError:
            continue
        # Catch scores reported late and games due in the next 48 hours.
        if timedelta(days=-2) <= day - today <= timedelta(days=2):
            return True
    return False
