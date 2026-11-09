"""Opt-in SQLite storage for FBM group snapshots (DEV, not wired into HA).

No network calls and no implicit following from a team lookup. Group identifiers
must be verified by the FBM adapter before use. Standard library only.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3


class FollowedGroups:
    """Atomic follow state and retained, timestamped official snapshots."""

    def __init__(self, path: str):
        self.path = str(path)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS groups (
                    season TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    followed INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (season, group_id)
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    season TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (season, group_id, source, observed_at),
                    FOREIGN KEY (season, group_id) REFERENCES groups(season, group_id)
                );
            """)

    def _db(self):
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys = ON")
        return db

    @staticmethod
    def _key(season, group_id):
        for value in (season, group_id):
            if not isinstance(value, str) or not value.strip() or len(value) > 128:
                raise ValueError("Se requieren IDs oficiales de temporada y grupo")
        return season.strip(), group_id.strip()

    def follow(self, season: str, group_id: str):
        season, group_id = self._key(season, group_id)
        with self._db() as db:
            db.execute("""INSERT INTO groups VALUES (?, ?, 1)
                          ON CONFLICT(season, group_id) DO UPDATE SET followed=1""",
                       (season, group_id))

    def unfollow(self, season: str, group_id: str):
        season, group_id = self._key(season, group_id)
        with self._db() as db:
            db.execute("UPDATE groups SET followed=0 WHERE season=? AND group_id=?",
                       (season, group_id))

    def followed(self):
        with self._db() as db:
            return db.execute("""SELECT season, group_id FROM groups
                                 WHERE followed=1 ORDER BY season, group_id""").fetchall()

    def record(self, season: str, group_id: str, source: str, payload: dict,
               *, observed_at: str | None = None) -> bool:
        """Record verified adapter output only when followed; never erase last good.

        Caller MUST verify the real official source, schema and ID mapping.
        Returns False when no longer followed. Only classification is currently
        validated; other sources must not be recorded by this DEV store.
        """
        season, group_id = self._key(season, group_id)
        if source != "clasificacion":
            raise ValueError("Fuente pendiente de validación real")
        if not isinstance(payload, dict) or not isinstance(payload.get("clasificacion"), list):
            raise ValueError("Clasificación inválida")
        stamped = observed_at or datetime.now(timezone.utc).isoformat()
        if not isinstance(stamped, str):
            raise ValueError("Marca temporal inválida")
        dt = datetime.fromisoformat(stamped.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("La marca temporal necesita zona horaria")
        stamped = dt.astimezone(timezone.utc).isoformat()
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        with self._db() as db:
            active = db.execute("SELECT followed FROM groups WHERE season=? AND group_id=?",
                                (season, group_id)).fetchone()
            if active is None or active[0] != 1:
                return False
            # An older response must not overwrite or be mistaken for fresh data.
            last = db.execute("""SELECT observed_at FROM snapshots
                                 WHERE season=? AND group_id=? AND source=?
                                 ORDER BY observed_at DESC LIMIT 1""",
                              (season, group_id, source)).fetchone()
            if last and stamped <= last[0]:
                return False
            db.execute("INSERT INTO snapshots VALUES (?, ?, ?, ?, ?)",
                       (season, group_id, source, stamped, encoded))
            return True

    def latest(self, season: str, group_id: str, source: str = "clasificacion"):
        season, group_id = self._key(season, group_id)
        with self._db() as db:
            row = db.execute("""SELECT s.observed_at, s.payload, g.followed
                                FROM snapshots s JOIN groups g
                                USING (season, group_id)
                                WHERE season=? AND group_id=? AND source=?
                                ORDER BY observed_at DESC LIMIT 1""",
                             (season, group_id, source)).fetchone()
        if row is None:
            return None
        return {"observed_at": row[0], "payload": json.loads(row[1]),
                "followed": bool(row[2]), "source": source}
