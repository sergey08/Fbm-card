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
                                           "complete": 0, "pending": 0}}
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
        for season, phase, group_id in selected:
            # Only the newest snapshot for each source/subject. Historical
            # versions must not inflate memory use as the archive grows.
            rows = db.execute(
                """SELECT s.source,s.subject,s.payload FROM snapshots AS s
                   WHERE s.season=? AND s.phase=? AND s.group_id=?
                     AND s.source IN ('standings','roster','player_stats')
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
                    if type(appearances) is not int or appearances < 1:
                        continue
                    counter["players"] += 1
                    stats = latest.get(("player_stats", player["id"]))
                    if stats is None:
                        counter["pending"] += 1
                        continue
                    payload = json.loads(stats)
                    games = payload.get("partidos", [])
                    if (isinstance(games, list) and len({game.get("id_partido") for game in games if isinstance(game, dict) and isinstance(game.get("id_partido"), str)}) >= appearances
                            and all(isinstance(game, dict) and
                                    type(game.get("puntos")) is int for game in games)):
                        counter["complete"] += 1
                    else:
                        counter["pending"] += 1
            for key in totals:
                totals[key] += counter[key]
            groups.append({"season_id": season, "phase_id": phase,
                           "group_id": group_id, **counter})
    return {"groups": groups, "totals": totals}
