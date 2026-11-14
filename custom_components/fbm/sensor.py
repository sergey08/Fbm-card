"""One small Home Assistant summary sensor per FBM config entry.

The MCP can read the sensor as a normal HA entity. Large team/player/match
datasets stay in local SQLite and admin-only WebSocket queries.
No FBM network access and no database creation during startup.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote
import json
import sqlite3

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .competition_coverage import read_coverage

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    async_add_entities([FBMCompetitionsSensor(hass, entry)], True)


def _round_status(fixtures: list[dict], today: date) -> dict:
    """Summarize the calendar without treating an isolated makeup as a round."""
    rounds: dict[int, list[tuple[date | None, str | None]]] = {}
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            continue
        number = fixture.get("jornada")
        if isinstance(number, str) and number.isdecimal() and len(number) < 5:
            number = int(number)
        if type(number) is not int or number < 1:
            continue
        value = fixture.get("fecha")
        played_on = None
        if isinstance(value, str):
            try:
                played_on = (datetime.strptime(value, "%d/%m/%Y").date()
                             if "/" in value else date.fromisoformat(value))
            except ValueError:
                pass
        rounds.setdefault(number, []).append((played_on, fixture.get("estado")))

    active, completed, upcoming = [], [], []
    for number, games in rounds.items():
        dates = sorted(day for day, state in games if day and state not in
                       ("postponed", "cancelled", "canceled"))
        if not dates:
            continue
        # Pick the date with most games, breaking ties towards the earlier date.
        # A split weekend counts as one round; isolated dates elsewhere do not.
        peak = min(set(dates), key=lambda day: (-dates.count(day), day))
        window = [day for day in dates if abs((day - peak).days) <= 2]
        if min(window) <= today <= max(window):
            active.append((abs((today - peak).days), -number, number))
        if max(dates) <= today and all(
            state in ("finished", "cancelled", "canceled") for _, state in games
        ):
            completed.append(number)
        if min(window) > today:
            upcoming.append((min(window), number))
    return {
        "current": min(active)[2] if active else None,
        "last_completed": max(completed) if completed else None,
        "next": min(upcoming)[1] if upcoming else None,
    }


def _read_competition_summary(path: str) -> dict:
    """Read existing SQLite in mode=ro; no migrations or file writes."""
    if not Path(path).is_file():
        return {"count": 0, "groups": []}
    uri = "file:" + quote(str(Path(path).resolve()), safe="/") + "?mode=ro"
    today = datetime.now(ZoneInfo("Europe/Madrid")).date()
    with sqlite3.connect(uri, uri=True) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(competitions)")}
        competition = "competition_name" if "competition_name" in columns else "''"
        groups = db.execute(
            f"""SELECT season, phase, group_id, phase_name, group_name,
                       team_name, {competition} FROM competitions
               WHERE followed=1 ORDER BY season, phase, group_id LIMIT 51"""
        ).fetchall()
        if len(groups) > 50:
            raise ValueError("Demasiadas competiciones seguidas")
        result = []
        for season, phase, group_id, phase_name, group_name, team_name, competition_name in groups:
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
            matches = json.loads(fixtures[1])["partidos"] if fixtures else []
            count_matches = len(matches) if fixtures else None
            # Compact, public sporting information for HA/MCP state reads.
            # No rosters, player IDs, photos or raw FBM response fields.
            ranking = []
            if standings:
                for item in json.loads(standings[1])["clasificacion"][:20]:
                    if type(item) is not dict:
                        continue
                    ranking.append({
                        key: item[key] for key in (
                            "id", "equipo", "posicion", "jugados",
                            "ganados", "perdidos", "puntos", "escudo"
                        ) if key in item and type(item[key]) in (str, int)
                    })
            recent_results = []
            if fixtures:
                for item in matches:
                    if (type(item) is not dict
                            or item.get("estado") != "finished"
                            or type(item.get("marcador")) is not dict):
                        continue
                    score = item["marcador"]
                    if (type(score.get("local")) is not int
                            or type(score.get("visitante")) is not int):
                        continue
                    recent_results.append({
                        "local": item.get("local"),
                        "visitante": item.get("visitante"),
                        "fecha": item.get("fecha"),
                        "marcador": {"local": score["local"],
                                    "visitante": score["visitante"]},
                    })
                recent_results = recent_results[-5:]
            result.append({
                "season_id": season, "phase_id": phase, "group_id": group_id,
                "phase_name": phase_name, "group_name": group_name,
                "team_name": team_name, "competition_name": competition_name,
                "teams": count_teams, "matches": count_matches,
                "standings_at": standings[0] if standings else None,
                "fixtures_at": fixtures[0] if fixtures else None,
                "ranking": ranking,
                "recent_results": recent_results,
                "round_status": _round_status(matches, today),
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

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        from homeassistant.helpers.dispatcher import async_dispatcher_connect
        from homeassistant.core import callback

        @callback
        def on_refresh() -> None:
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(async_dispatcher_connect(
            self.hass, f"fbm_competitions_refresh_{self._entry_id}", on_refresh))

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
        try:
            coverage = await self.hass.async_add_executor_job(
                read_coverage, entry["competitions_sqlite_path"])
        except (OSError, ValueError, KeyError, sqlite3.Error, TypeError):
            coverage = {"groups": [], "totals": {}, "status": "unavailable"}
        self._attr_available = True
        self._attr_native_value = summary["count"]
        # Keep the exposed state deliberately bounded. The actual roster,
        # fixtures and full analysis remain in the archive.
        auto_groups, auto_players = entry.get("auto_sync_flags", (False, False))
        updater = entry.get("auto_updater")
        health = updater.health if updater is not None else {}
        checked = updater.group_checked_at if updater is not None else {}
        for group in summary["groups"]:
            group["last_checked_at"] = checked.get(group["group_id"])
        self._attr_extra_state_attributes = {
            "groups": summary["groups"],
            "coverage": coverage,
            "automatic_refresh": {
                "groups_enabled": auto_groups,
                "players_enabled": auto_players,
                "groups": dict(health.get("groups", {})),
                "players": dict(health.get("players", {})),
            },
        }
