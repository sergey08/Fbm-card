"""One small Home Assistant summary sensor per FBM config entry.

The MCP can read the sensor as a normal HA entity. Large team/player/match
datasets stay in local SQLite and admin-only WebSocket queries.
No FBM network access and no database creation during startup.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    async_add_entities([FBMCompetitionsSensor(hass, entry)], True)


def _read_competition_summary(path: str, archive_type) -> dict:
    """Executor-only, read-only summary (no images or player details)."""
    if not Path(path).is_file():
        return {"count": 0, "groups": []}
    archive = archive_type(path)
    groups = archive.followed()
    if len(groups) > 50:
        raise ValueError("Demasiadas competiciones seguidas")
    result = []
    for group in groups:
        ident = {**group, "season_verified": True}
        standing = archive.latest(ident, "standings")
        fixtures = archive.latest(ident, "fixtures")
        result.append({
            "season_id": group["season_id"],
            "phase_id": group["phase_id"],
            "group_id": group["group_id"],
            "teams": (len(standing["payload"]["clasificacion"])
                      if standing is not None else None),
            "matches": (len(fixtures["payload"]["partidos"])
                        if fixtures is not None else None),
            "standings_at": standing["observed_at"] if standing else None,
            "fixtures_at": fixtures["observed_at"] if fixtures else None,
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
                entry["competitions_archive_factory"],
            )
        except (OSError, ValueError):
            self._attr_available = False
            return
        self._attr_available = True
        self._attr_native_value = summary["count"]
        # Keep the exposed state deliberately bounded. The actual roster,
        # fixtures and full analysis remain in the archive.
        self._attr_extra_state_attributes = {"groups": summary["groups"]}
