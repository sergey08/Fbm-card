"""Persist verified FBM competition-group snapshots without photographs.

Explicit opt-in only. The season, phase and group identifiers MUST come from
verified official FBM data. No inferred season, automatic polling or raw DTOs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3


class CompetitionArchive:
    """Versioned snapshots deduplicated by verified competition identity."""

    SOURCES = frozenset({"standings", "fixtures", "roster"})
    MAX_JSON_BYTES = 1024 * 1024

    def __init__(self, path: str):
        self.path = str(path)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS competitions (
                    season TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    followed INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (season, phase, group_id)
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    season TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    subject TEXT NOT NULL DEFAULT '',
                    observed_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (season, phase, group_id, source, subject, observed_at),
                    FOREIGN KEY (season, phase, group_id)
                      REFERENCES competitions (season, phase, group_id)
                );
                CREATE INDEX IF NOT EXISTS idx_fbm_recent
                  ON snapshots (season, phase, group_id, source, subject, observed_at DESC);
            """)

    def _db(self):
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _identity(identity: dict) -> tuple[str, str, str]:
        if type(identity) is not dict or identity.get("season_verified") is not True:
            raise ValueError("La temporada oficial aún no está verificada")
        fields = (identity.get("season_id"), identity.get("phase_id"), identity.get("group_id"))
        if any(type(v) is not str or not v.strip() or len(v) > 128 for v in fields):
            raise ValueError("Identidad oficial incompleta")
        return tuple(v.strip() for v in fields)

    def follow(self, identity: dict):
        key = self._identity(identity)
        with self._db() as db:
            db.execute("""INSERT INTO competitions VALUES (?, ?, ?, 1)
                ON CONFLICT(season,phase,group_id) DO UPDATE SET followed=1""", key)
        return key

    def unfollow(self, identity: dict):
        key = self._identity(identity)
        with self._db() as db:
            db.execute("UPDATE competitions SET followed=0 WHERE season=? AND phase=? AND group_id=?", key)

    def followed(self):
        with self._db() as db:
            rows = db.execute("""SELECT season,phase,group_id FROM competitions
                                 WHERE followed=1 ORDER BY season,phase,group_id""").fetchall()
        return [{"season_id": s, "phase_id": p, "group_id": g} for s,p,g in rows]

    def record(self, identity: dict, source: str, payload: dict, *,
               subject: str = "", observed_at: str | None = None) -> bool:
        key = self._identity(identity)
        if source not in self.SOURCES or type(payload) is not dict:
            raise ValueError("Fuente de datos no autorizada")
        expected = {"standings": "clasificacion", "fixtures": "partidos", "roster": "jugadores"}[source]
        if type(payload.get(expected)) is not list:
            raise ValueError("Datos normalizados incompletos")
        if source != "roster" and subject:
            raise ValueError("El sujeto solo se usa para plantillas")
        if source == "roster" and (type(subject) is not str or not subject or len(subject) > 512):
            raise ValueError("ID de equipo no válido")
        # Persist explicit normalized sporting fields only. This excludes
        # photographs, image URLs, original DTO extras and future unknown fields.
        approved = {
            "standings": {"id", "equipo", "posicion", "jugados", "ganados",
                          "perdidos", "puntos"},
            "fixtures": {"id", "local", "visitante", "fecha", "hora",
                         "fecha_hora_utc", "campo", "direccion", "estado",
                         "estado_oficial", "jornada", "marcador"},
            "roster": {"id", "nombre", "equipo", "temporada",
                       "partidos_jugados", "puntos_totales", "media_puntos",
                       "puntos_por_partido", "minutos_por_partido"},
        }[source]
        output_key = {"standings": "clasificacion", "fixtures": "partidos",
                      "roster": "jugadores"}[source]
        clean = []
        for row in payload[output_key]:
            if type(row) is not dict:
                raise ValueError("Registro deportivo inválido")
            clean.append({k: v for k, v in row.items() if k in approved})
        payload = {output_key: clean}
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode("utf-8")) > self.MAX_JSON_BYTES:
            raise ValueError("Instantánea demasiado grande")
        timestamp = observed_at or datetime.now(timezone.utc).isoformat()
        at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if at.tzinfo is None:
            raise ValueError("Se requiere fecha con zona horaria")
        timestamp = at.astimezone(timezone.utc).isoformat()
        with self._db() as db:
            active = db.execute("""SELECT followed FROM competitions
                        WHERE season=? AND phase=? AND group_id=?""", key).fetchone()
            if not active or active[0] != 1:
                return False
            latest = db.execute("""SELECT observed_at, payload FROM snapshots WHERE
                season=? AND phase=? AND group_id=? AND source=? AND subject=?
                ORDER BY observed_at DESC LIMIT 1""", (*key, source, subject)).fetchone()
            if latest and (timestamp <= latest[0] or encoded == latest[1]):
                return False
            db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)",
                       (*key, source, subject, timestamp, encoded))
            return True

    def latest(self, identity: dict, source: str, subject: str = ""):
        key = self._identity(identity)
        if source not in self.SOURCES:
            raise ValueError("Fuente no autorizada")
        with self._db() as db:
            row = db.execute("""SELECT observed_at,payload FROM snapshots
                WHERE season=? AND phase=? AND group_id=? AND source=? AND subject=?
                ORDER BY observed_at DESC LIMIT 1""",
                (*key, source, subject)).fetchone()
        return {"observed_at": row[0], "payload": json.loads(row[1])} if row else None
