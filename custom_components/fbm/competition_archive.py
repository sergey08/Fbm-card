"""Persist verified FBM competition-group snapshots without photographs.

Explicit opt-in only. The season, phase and group identifiers MUST come from
verified official FBM data. No inferred season, automatic polling or raw DTOs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from urllib.parse import urlsplit, parse_qs

from .image_references import image_data_uri


def _official_team_crest(value):
    """Accept only a genuine full FBM crest URL, never opaque references."""
    if type(value) is not str or not 0 < len(value) <= 1024:
        return None
    try:
        url = urlsplit(value)
        if (url.scheme != "https" or url.username or url.password
                or url.port is not None or url.fragment):
            return None
        if url.hostname == "appaficionfbm.gesdeportiva.es":
            if url.path.lower() != "/imagenes.ashx":
                return None
            params = parse_qs(url.query, keep_blank_values=True)
            if (set(params) != {"tipo", "id"} or
                    params["tipo"] != ["escudo"] or
                    len(params["id"]) != 1 or
                    not params["id"][0] or len(params["id"][0]) > 256 or
                    not params["id"][0].isascii() or
                    not params["id"][0].isalnum()):
                return None
            return value
        if url.hostname in {"fbm.es", "www.fbm.es"}:
            if not url.path.lower().endswith((".png", ".webp", ".jpg", ".jpeg")):
                return None
            if url.query:
                return None
            return value
    except (ValueError, AttributeError):
        return None
    return None


class CompetitionArchive:
    """Versioned snapshots deduplicated by verified competition identity."""

    SOURCES = frozenset({"standings", "fixtures", "roster", "player_stats"})
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
                    anchor_team_id TEXT NOT NULL DEFAULT '',
                    team_name TEXT NOT NULL DEFAULT '',
                    phase_name TEXT NOT NULL DEFAULT '',
                    group_name TEXT NOT NULL DEFAULT '',
                    competition_name TEXT NOT NULL DEFAULT '',
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
            # Migrate development databases created before anchor support.
            columns = {
                row[1] for row in db.execute("PRAGMA table_info(competitions)")
            }
            if "anchor_team_id" not in columns:
                db.execute(
                    "ALTER TABLE competitions ADD COLUMN anchor_team_id TEXT NOT NULL DEFAULT ''"
                )
            for label in ("team_name", "phase_name", "group_name", "competition_name"):
                if label not in columns:
                    db.execute(
                        f"ALTER TABLE competitions ADD COLUMN {label} TEXT NOT NULL DEFAULT ''"
                    )

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

    def follow(self, identity: dict, anchor_team_id: str = "",
               display: dict | None = None):
        """Opt in and keep short public labels separate from opaque API keys."""
        key = self._identity(identity)
        if (type(anchor_team_id) is not str or len(anchor_team_id) > 512
                or (anchor_team_id and not anchor_team_id.strip())):
            raise ValueError("Equipo de referencia inválido")
        labels = []
        for field in ("team_name", "phase_name", "group_name", "competition_name"):
            label = (display or {}).get(field, "")
            if type(label) is not str or len(label) > 120:
                raise ValueError("Nombre visible inválido")
            labels.append(label.strip())
        with self._db() as db:
            db.execute(
                """INSERT INTO competitions
                   (season, phase, group_id, followed, anchor_team_id,
                    team_name, phase_name, group_name, competition_name)
                   VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
                   ON CONFLICT(season,phase,group_id) DO UPDATE SET
                      followed=1,
                      anchor_team_id=CASE WHEN excluded.anchor_team_id <> ''
                        THEN excluded.anchor_team_id ELSE competitions.anchor_team_id END,
                      team_name=CASE WHEN excluded.team_name <> ''
                        THEN excluded.team_name ELSE competitions.team_name END,
                      phase_name=CASE WHEN excluded.phase_name <> ''
                        THEN excluded.phase_name ELSE competitions.phase_name END,
                      group_name=CASE WHEN excluded.group_name <> ''
                        THEN excluded.group_name ELSE competitions.group_name END,
                      competition_name=CASE WHEN excluded.competition_name <> ''
                        THEN excluded.competition_name ELSE competitions.competition_name END""",
                (*key, anchor_team_id, *labels),
            )
        return key

    def followed_with_anchor(self):
        """Admin manager metadata; internal IDs are not displayed in the UI."""
        with self._db() as db:
            rows = db.execute(
                """SELECT season,phase,group_id,anchor_team_id,
                          team_name,phase_name,group_name,competition_name
                   FROM competitions WHERE followed=1
                   ORDER BY season,phase,group_id"""
            ).fetchall()
        return [
            {"season_id": season, "phase_id": phase, "group_id": group,
             "anchor_team_id": anchor, "team_name": team,
             "phase_name": phase_label, "group_name": group_label,
             "competition_name": competition_label}
            for season,phase,group,anchor,team,phase_label,group_label,competition_label in rows
        ]

    def update_display(self, identity: dict, display: dict):
        """Refresh public labels only for an actively followed competition."""
        key = self._identity(identity)
        if type(display) is not dict:
            raise ValueError("Etiquetas inválidas")
        labels = []
        for field in ("team_name", "phase_name", "group_name", "competition_name"):
            value = display.get(field, "")
            if type(value) is not str or len(value) > 120:
                raise ValueError("Etiqueta inválida")
            labels.append(value.strip())
        with self._db() as db:
            db.execute(
                """UPDATE competitions SET
                   team_name=CASE WHEN ?<>'' THEN ? ELSE team_name END,
                   phase_name=CASE WHEN ?<>'' THEN ? ELSE phase_name END,
                   group_name=CASE WHEN ?<>'' THEN ? ELSE group_name END,
                   competition_name=CASE WHEN ?<>'' THEN ? ELSE competition_name END
                   WHERE season=? AND phase=? AND group_id=? AND followed=1""",
                (*(value for label in labels for value in (label, label)), *key),
            )

    def selected_for_team(self, team_id: str, phase_id: str, group_id: str):
        """Resolve a consented group by stored official team and phase/group.

        Return None if there are no matches or if the identity is ambiguous.
        An unselected team cannot create or update another competition.
        """
        if (type(team_id) is not str or not team_id.strip() or len(team_id) > 512
                or type(phase_id) is not str or not phase_id.strip()
                or type(group_id) is not str or not group_id.strip()):
            raise ValueError("Equipo o grupo no válido")
        with self._db() as db:
            rows = db.execute(
                """SELECT season,phase,group_id FROM competitions
                   WHERE followed=1 AND anchor_team_id=?
                   AND phase=? AND group_id=?""",
                (team_id, phase_id, group_id),
            ).fetchall()
        if len(rows) != 1:
            return None
        return {"season_id": rows[0][0], "phase_id": rows[0][1],
                "group_id": rows[0][2], "season_verified": True}

    def is_followed(self, identity: dict) -> bool:
        """Check explicit opt-in without changing the archive."""
        key = self._identity(identity)
        with self._db() as db:
            row = db.execute(
                """SELECT followed FROM competitions
                   WHERE season=? AND phase=? AND group_id=?""", key
            ).fetchone()
        return bool(row is not None and row[0] == 1)

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
        expected = {"standings": "clasificacion", "fixtures": "partidos", "roster": "jugadores", "player_stats": "partidos"}[source]
        if type(payload.get(expected)) is not list:
            raise ValueError("Datos normalizados incompletos")
        if source in ("standings", "fixtures") and subject:
            raise ValueError("El sujeto solo se usa para plantillas o estadísticas")
        if source in ("roster", "player_stats") and (type(subject) is not str or not subject or len(subject) > 512):
            raise ValueError("ID de equipo no válido")
        if source == "player_stats":
            # These are normalized, per-match sporting numbers only. The
            # player ID is the snapshot subject; do not duplicate names,
            # personal profile or network DTOs in each match.
            allowed = {"id_partido", "fecha", "rival", "local", "puntos",
                       "asistencias", "faltas_cometidas", "faltas_recibidas",
                       "rebotes", "rebotes_defensivos", "rebotes_ofensivos",
                       "recuperaciones", "perdidas", "valoracion"}
            matches = []
            for match in payload["partidos"]:
                if type(match) is not dict:
                    raise ValueError("Estadística de partido inválida")
                ident = match.get("id_partido")
                if type(ident) is not str or not ident or len(ident) > 512:
                    raise ValueError("Partido sin identificador")
                clean = {k: v for k, v in match.items() if k in allowed}
                for field in ("puntos", "asistencias", "faltas_cometidas",
                              "faltas_recibidas", "rebotes", "rebotes_defensivos",
                              "rebotes_ofensivos", "recuperaciones", "perdidas",
                              "valoracion"):
                    value = clean.get(field)
                    if value is not None and (type(value) not in (int, float)
                            or abs(value) > 10000):
                        raise ValueError("Estadística inválida")
                matches.append(clean)
            if len(matches) > 1000 or len({m["id_partido"] for m in matches}) != len(matches):
                raise ValueError("Partidos repetidos o excesivos")
            globals_input = payload.get("globales")
            global_allowed = {"puntos_totales", "media_puntos", "asistencias",
                              "faltas_cometidas", "faltas_recibidas", "rebotes",
                              "rebotes_defensivos", "rebotes_ofensivos",
                              "recuperaciones", "perdidas", "valoracion"}
            if type(globals_input) is not dict:
                raise ValueError("Estadísticas globales incompletas")
            global_clean = {}
            for k in global_allowed:
                value = globals_input.get(k)
                if value is not None and (type(value) not in (int, float)
                        or abs(value) > 1000000):
                    raise ValueError("Estadística global inválida")
                global_clean[k] = value
            payload = {"globales": global_clean, "partidos": matches}
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
            if len(encoded.encode("utf-8")) > self.MAX_JSON_BYTES:
                raise ValueError("Instantánea demasiado grande")
            return self._write_snapshot(key, source, subject, encoded, observed_at)
        # Persist normalized sporting fields. Only explicit, verified official
        # club-crest URLs may be retained; exclude player photos and raw DTOs.
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
        crests = {}
        crest_chars = 0
        for row in payload[output_key]:
            if type(row) is not dict:
                raise ValueError("Registro deportivo inválido")
            item = {k: v for k, v in row.items() if k in approved}
            if source == "standings":
                crest = _official_team_crest(row.get("escudo"))
                if crest:
                    item["escudo"] = crest
            elif source == "fixtures":
                for side in ("local", "visitante"):
                    name = row.get(side)
                    if not isinstance(name, str) or not name or name in crests:
                        continue
                    image = row.get(f"img_{side}")
                    reference = row.get(f"escudo_{side}")
                    crest = (_official_team_crest(image)
                             or _official_team_crest(reference)
                             or image_data_uri(image, max_bytes=65536))
                    if crest and crest_chars + len(crest) <= 256 * 1024:
                        crests[name] = crest
                        crest_chars += len(crest)
            clean.append(item)
        payload = {output_key: clean}
        if crests:
            payload["escudos"] = crests
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode("utf-8")) > self.MAX_JSON_BYTES:
            raise ValueError("Instantánea demasiado grande")
        return self._write_snapshot(key, source, subject, encoded, observed_at)

    def _write_snapshot(self, key, source, subject, encoded, observed_at):
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
