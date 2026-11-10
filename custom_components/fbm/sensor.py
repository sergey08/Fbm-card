"""One small Home Assistant summary sensor per FBM config entry.

The MCP can read the sensor as a normal HA entity. Large team/player/match
datasets stay in local SQLite and admin-only WebSocket queries.
No FBM network access and no database creation during startup.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from urllib.parse import quote
import json
import sqlite3

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    async_add_entities([FBMCompetitionsSensor(hass, entry)], True)


def _read_competition_summary(path: str) -> dict:
    """Read existing SQLite in mode=ro; no migrations or file writes."""
    if not Path(path).is_file():
        return {"count": 0, "groups": []}
    uri = "file:" + quote(str(Path(path).resolve()), safe="/") + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        groups = db.execute(
            """SELECT season, phase, group_id FROM competitions
               WHERE followed=1 ORDER BY season, phase, group_id LIMIT 51"""
        ).fetchall()
        if len(groups) > 50:
            raise ValueError("Demasiadas competiciones seguidas")
        result = []
        for season, phase, group_id in groups:
            snapshots = []
            for source in ("standings", "fixtures"):
                record = db.execute(
                    """SELECT observed_at, payload FROM snapshots WHERE
                       season=? AND phase=? AND group_id=?
                       AND source=? AND subject=''
                       ORDER BY observed_at DESC LIMIT 1""",
                    (season, phase, group_id, source),
                ).fetchone()
                snapshots.append(record)
            standings, fixtures = snapshots
            count_teams = (len(json.loads(standings[1])["clasificacion"])
                           if standings else None)
            count_matches = (len(json.loads(fixtures[1])["partidos"])
                             if fixtures else None)
            result.append({
                "season_id": season, "phase_id": phase, "group_id": group_id,
                "teams": count_teams, "matches": count_matches,
                "standings_at": standings[0] if standings else None,
                "fixtures_at": fixtures[0] if fixtures else None,
            })
    return {"count": len(groups), "groups": result}


class FBMCompetitionsSensor(SensorEntity):
    """Summarizes followed groups, without storing bulky HA attributes."""

    _attr_has_entity_name = True
    _attr_name = "Competiciones"
    _attr_icon = "mdi:basketball"
    _attr_native_value = 0

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"fbm_{entry.entry_id}_competitions"
        self._attr_extra_state_attributes = {"groups": []}

    async def async_update(self) -> None:
        entry = self.hass.data.get(DOMAIN, {}).get(self._entry_id)
        if not isinstance(entry, dict):
            self._attr_available = False
            return
        try:
            summary = await self.hass.async_add_executor_job(
                _read_competition_summary,
                entry["competitions_sqlite_path"],
            )
        except (OSError, ValueError, KeyError, sqlite3.Error):
            self._attr_available = False
            return
        self._attr_available = True
        self._attr_native_value = summary["count"]
        # Keep the exposed state deliberately bounded. The actual roster,
        # fixtures and full analysis remain in the archive.
        self._attr_extra_state_attributes = {"groups": summary["groups"]}
