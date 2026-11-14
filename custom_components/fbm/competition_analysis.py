"""Sport-only analytics from verified archived FBM group snapshots.

No requests to FBM, inferred player statistics or photo data.
"""
from __future__ import annotations

import unicodedata


def competition_analysis(standings: dict, fixtures: dict,
                         rosters: dict[str, dict] | None = None,
                         individual_stats: dict[str, dict] | None = None) -> dict:
    """Compare all group participants from latest official normalized data.

    Counts from standings are authoritative; fixture calculations only use
    matches with an explicit finished state and numeric final score.
    """
    ranking = standings.get("clasificacion") if type(standings) is dict else None
    matches = fixtures.get("partidos") if type(fixtures) is dict else None
    if type(ranking) is not list or type(matches) is not list:
        raise ValueError("Faltan datos oficiales de clasificación o partidos")
    if len(ranking) > 100 or len(matches) > 2000:
        raise ValueError("Datos deportivos fuera de límites")
    teams, seen = [], set()
    for row in ranking:
        if type(row) is not dict:
            raise ValueError("Equipo no válido")
        ident, name = row.get("id"), row.get("equipo")
        if (type(ident) is not str or not ident.strip()
                or type(name) is not str or not name.strip() or ident in seen):
            raise ValueError("Participante no identificado de forma única")
        seen.add(ident)
        teams.append({
            "id": ident, "nombre": name, "posicion": row.get("posicion"),
            "jugados": row.get("jugados"), "ganados": row.get("ganados"),
            "perdidos": row.get("perdidos"), "puntos": row.get("puntos"),
        })
    # Official FBM standings and fixture labels sometimes differ only by
    # accents/case/spacing (e.g. AMORÓS vs AMOROS). Normalize conservatively:
    # never match two teams that collapse to the same canonical label.
    def canonical_name(value):
        if type(value) is not str:
            return None
        decomposed = unicodedata.normalize("NFKD", value)
        folded = "".join(char for char in decomposed
                         if not unicodedata.combining(char)).casefold()
        return " ".join(folded.split())

    by_name = {}
    for team in teams:
        by_name.setdefault(canonical_name(team["nombre"]), []).append(team)
    unique = {name: rows[0] for name, rows in by_name.items()
              if name is not None and len(rows) == 1}
    stats = {team["id"]: {"finalizados_con_marcador": 0,
                          "puntos_favor": 0, "puntos_contra": 0}
             for team in teams}
    finished_ids = set()
    finished_games = []
    team_game_ids = {team["id"]: set() for team in teams}
    for match in matches:
        if type(match) is not dict or match.get("estado") != "finished":
            continue
        match_id = match.get("id")
        score = match.get("marcador")
        if (type(match_id) is not str or not match_id or match_id in finished_ids
                or type(score) is not dict):
            continue
        local, visitor = match.get("local"), match.get("visitante")
        a, b = score.get("local"), score.get("visitante")
        if (type(a) is not int or type(b) is not int or a < 0 or b < 0
                or a > 500 or b > 500 or local == visitor
                or canonical_name(local) not in unique
                or canonical_name(visitor) not in unique):
            continue
        finished_ids.add(match_id)
        finished_games.append((match_id, match.get("fecha"), local, visitor, a, b))
        for name, pf, pc in ((local, a, b), (visitor, b, a)):
            rec = stats[unique[canonical_name(name)]["id"]]
            rec["finalizados_con_marcador"] += 1
            team_game_ids[unique[canonical_name(name)]["id"]].add(match_id)
            rec["puntos_favor"] += pf
            rec["puntos_contra"] += pc

    for team in teams:
        data = stats[team["id"]]
        n = data["finalizados_con_marcador"]
        team["partidos_con_marcador"] = n
        team["media_favor"] = round(data["puntos_favor"] / n, 2) if n else None
        team["media_contra"] = round(data["puntos_contra"] / n, 2) if n else None
        team["diferencia_media"] = round((data["puntos_favor"] - data["puntos_contra"]) / n, 2) if n else None
    leaders = []
    rosters = rosters or {}
    for team in teams:
        record = rosters.get(team["id"])
        members = record.get("jugadores") if type(record) is dict else None
        if type(members) is not list or len(members) > 100:
            continue
        for member in members:
            if type(member) is not dict:
                continue
            points = member.get("puntos_totales")
            if type(points) is not int or points < 0:
                continue
            ident = member.get("id")
            name = member.get("nombre")
            if type(ident) is not str or type(name) is not str:
                continue
            leaders.append({"jugador_id": ident, "jugador": name,
                            "equipo_id": team["id"], "equipo": team["nombre"],
                            "puntos_totales": points})
    # Optional per-match data supplements absent global totals. Only
    # aggregate explicit numeric points and report how many matches actually
    # supplied a score, never interpret null as a zero.
    individual_stats = individual_stats or {}
    covered = 0
    for team in teams:
        members = (rosters.get(team["id"]) or {}).get("jugadores", [])
        for member in members:
            player_id = member.get("id") if type(member) is dict else None
            if type(player_id) is not str:
                continue
            record = individual_stats.get(player_id)
            matches = record.get("partidos") if type(record) is dict else None
            if type(matches) is not list:
                continue
            explicit = [m["puntos"] for m in matches
                        if type(m) is dict and type(m.get("puntos")) is int
                        and m["puntos"] >= 0]
            if not explicit:
                continue
            covered += 1
            if any(row["jugador_id"] == player_id for row in leaders):
                continue
            leaders.append({
                "jugador_id": player_id, "jugador": member.get("nombre"),
                "equipo_id": team["id"], "equipo": team["nombre"],
                "puntos_totales": sum(explicit),
                "partidos_con_puntos": len(explicit),
                "origen": "suma_de_partidos_disponibles",
            })
    per_team_game = {team["id"]: {} for team in teams}
    # Validate scorer coverage against the actual finished fixture IDs.
    # A successful download is NOT proof that every team point is attributed.
    # Do not expose private player data in team-level coverage diagnostics.
    for team in teams:
        members = (rosters.get(team["id"]) or {}).get("jugadores")
        team["cobertura_anotacion"] = {
            "jugadoras_plantilla": len(members) if type(members) is list else None,
            "jugadoras_con_partidos_puntuados": 0,
            "puntos_atribuidos": None,
            "puntos_marcador": stats[team["id"]]["puntos_favor"]
                               if stats[team["id"]]["finalizados_con_marcador"] else None,
            "puntos_sin_atribuir": None,
            "cobertura_completa": None,
        }
        if type(members) is not list or not team_game_ids[team["id"]]:
            continue
        attributed = 0
        with_points = 0
        for member in members:
            if type(member) is not dict or type(member.get("id")) is not str:
                continue
            record = individual_stats.get(member["id"])
            game_rows = record.get("partidos") if type(record) is dict else None
            if type(game_rows) is not list:
                continue
            used = set()
            found = False
            for row in game_rows:
                if type(row) is not dict:
                    continue
                game_id = row.get("id_partido")
                pts = row.get("puntos")
                if (type(game_id) is str and game_id in team_game_ids[team["id"]]
                        and game_id not in used and type(pts) is int
                        and 0 <= pts <= 500):
                    used.add(game_id)
                    attributed += pts
                    totals = per_team_game[team["id"]]
                    game_sum = totals.setdefault(game_id, {"puntos": 0, "jugadores": 0})
                    game_sum["puntos"] += pts
                    game_sum["jugadores"] += 1
                    found = True
            if found:
                with_points += 1
        if not with_points:
            continue
        match_points = stats[team["id"]]["puntos_favor"]
        item = team["cobertura_anotacion"]
        item["jugadoras_con_partidos_puntuados"] = with_points
        item["puntos_atribuidos"] = attributed
        item["puntos_sin_atribuir"] = match_points - attributed
        item["cobertura_completa"] = (attributed == match_points)
    # Show exceptional fixtures without changing any FBM score or assigning
    # missing points. Never call the API here, and never leak player IDs.
    # The discrepancy is unknown when no individual records exist at all.
    anomalous_matches = []
    for game_id, game_date, home_name, away_name, home_pts, away_pts in finished_games:
        participants = []
        for name, official in ((home_name, home_pts), (away_name, away_pts)):
            team = unique[canonical_name(name)]
            observed = per_team_game[team["id"]].get(game_id)
            participants.append({
                "equipo": team["nombre"],
                "puntos_marcador": official,
                "puntos_individuales": observed["puntos"] if observed else None,
                "jugadores_con_registro": observed["jugadores"] if observed else 0,
                "diferencia": official - observed["puntos"] if observed else None,
            })
        if any(side["diferencia"] not in (None, 0) for side in participants):
            anomalous_matches.append({
                "fecha": game_date,
                "local": home_name,
                "visitante": away_name,
                "equipos": participants,
                "ambos_equipos_con_desajuste": all(
                    side["diferencia"] not in (None, 0) for side in participants),
            })
    # Keep WebSocket responses bounded even if an older archive contains
    # many games with partial individual coverage.
    anomaly_count = len(anomalous_matches)
    anomalous_matches = anomalous_matches[:40]
    leaders.sort(key=lambda item: (-item["puntos_totales"], item["jugador_id"]))
    return {
        "equipos": teams, "numero_equipos": len(teams),
        "partidos_con_marcador": len(finished_ids),
        "anotadores": leaders,
        "plantillas_disponibles": sum(
            1 for team in teams if type(rosters.get(team["id"])) is dict),
        "jugadores_con_puntos_por_partido": covered,
        "partidos_con_desajuste_individual": anomaly_count,
        "incidencias_anotacion_partidos": anomalous_matches,
        "aviso": "Solo estadísticas publicadas por FBM; las ausentes no se estiman.",
    }
