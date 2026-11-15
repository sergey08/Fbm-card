"""Read-only, bounded coverage counters for followed FBM competitions.

Never exposes player identities, names or raw statistics to HA attributes.
Counts only already archived snapshots; no network calls or SQLite writes.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import quote


def read_coverage(path: str) -> dict:
    if not Path(path).is_file():
        return {"groups": [], "totals": {"teams": 0, "rosters": 0, "players": 0,
                                           "complete": 0, "pending": 0, "missing_rosters": 0,
                                           "coverage_percent": None}}
    uri = "file:" + quote(str(Path(path).resolve()), safe="/") + "?mode=ro"
    groups = []
    totals = {"teams": 0, "rosters": 0, "players": 0, "complete": 0, "pending": 0}
    with sqlite3.connect(uri, uri=True) as db:
        selected = db.execute(
            """SELECT season, phase, group_id FROM competitions
               WHERE followed=1 ORDER BY season,phase,group_id LIMIT 51"""
        ).fetchall()
        if len(selected) > 50:
            raise ValueError("Too many followed competitions")
        tracks_failures = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='player_stats_failures'"
        ).fetchone() is not None
        for season, phase, group_id in selected:
            failures = set()
            if tracks_failures:
                failures = {row[0] for row in db.execute(
                    """SELECT subject FROM player_stats_failures
                       WHERE season=? AND phase=? AND group_id=?""",
                    (season, phase, group_id),
                )}
            # Only the newest snapshot for each source/subject. Historical
            # versions must not inflate memory use as the archive grows.
            rows = db.execute(
                """SELECT s.source,s.subject,s.payload FROM snapshots AS s
                   WHERE s.season=? AND s.phase=? AND s.group_id=?
                     AND s.source IN ('standings','fixtures','roster','player_stats')
                     AND s.observed_at=(
                       SELECT MAX(t.observed_at) FROM snapshots AS t
                       WHERE t.season=s.season AND t.phase=s.phase
                         AND t.group_id=s.group_id AND t.source=s.source
                         AND t.subject=s.subject
                     )""",
                (season, phase, group_id),
            ).fetchall()
            latest = {(source, subject): payload
                      for source, subject, payload in rows}
            standings_raw = latest.get(("standings", ""))
            standings = json.loads(standings_raw).get("clasificacion", []) if standings_raw else []
            teams = [r for r in standings[:20] if isinstance(r, dict) and isinstance(r.get("id"), str)]
            counter = {"teams": len(teams), "rosters": 0, "players": 0,
                       "complete": 0, "pending": 0}
            fixtures_raw = latest.get(("fixtures", ""))
            fixtures = json.loads(fixtures_raw).get("partidos", []) if fixtures_raw else []
            details = {
                "standings_archived": standings_raw is not None,
                "calendar_archived": fixtures_raw is not None,
                "fixtures_archived": len(fixtures),
                "rounds_archived": len({game["jornada"] for game in fixtures
                                        if type(game.get("jornada")) is int}),
                "roster_entries": 0,
                "zero_appearances": 0,
                "unknown_appearances": 0,
                "stats_not_archived": 0,
                "stats_empty": 0,
                "stats_incomplete": 0,
                "stats_last_attempt_failed": 0,
            }
            for team in teams:
                raw = latest.get(("roster", team["id"]))
                if raw is None:
                    continue
                counter["rosters"] += 1
                roster = json.loads(raw).get("jugadores", [])
                for player in roster[:100]:
                    if not isinstance(player, dict) or not isinstance(player.get("id"), str):
                        continue
                    appearances = player.get("partidos_jugados")
                    details["roster_entries"] += 1
                    if player["id"] in failures:
                        details["stats_last_attempt_failed"] += 1
                    if type(appearances) is not int or appearances < 0:
                        details["unknown_appearances"] += 1
                        continue
                    if appearances == 0:
                        details["zero_appearances"] += 1
                        continue
                    counter["players"] += 1
                    stats = latest.get(("player_stats", player["id"]))
                    if stats is None:
                        details["stats_not_archived"] += 1
                        counter["pending"] += 1
                        continue
                    payload = json.loads(stats)
                    games = payload.get("partidos", [])
                    if (isinstance(games, list) and len({game.get("id_partido") for game in games if isinstance(game, dict) and isinstance(game.get("id_partido"), str)}) >= appearances
                            and all(isinstance(game, dict) and
                                    type(game.get("puntos")) is int for game in games)):
                        counter["complete"] += 1
                    else:
                        key = "stats_empty" if games == [] else "stats_incomplete"
                        details[key] += 1
                        counter["pending"] += 1
            counter["missing_rosters"] = counter["teams"] - counter["rosters"]
            counter["coverage_percent"] = (
                round(100 * counter["complete"] / counter["players"], 1)
                if counter["players"] and counter["missing_rosters"] == 0
                else None
            )
            for key in totals:
                totals[key] += counter[key]
            groups.append({"season_id": season, "phase_id": phase,
                           "group_id": group_id, **counter, "archive": details})
    totals["missing_rosters"] = totals["teams"] - totals["rosters"]
    totals["coverage_percent"] = (
        round(100 * totals["complete"] / totals["players"], 1)
        if totals["players"] and totals["missing_rosters"] == 0
        else None
    )
    return {"groups": groups, "totals": totals}
