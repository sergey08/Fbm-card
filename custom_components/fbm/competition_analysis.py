"""Sport-only analytics from verified archived FBM group snapshots.

No requests to FBM, inferred player statistics or photo data.
"""
from __future__ import annotations

import unicodedata


def competition_analysis(standings: dict, fixtures: dict,
                         rosters: dict[str, dict] | None = None) -> dict:
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
        for name, pf, pc in ((local, a, b), (visitor, b, a)):
            rec = stats[unique[canonical_name(name)]["id"]]
            rec["finalizados_con_marcador"] += 1
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
    leaders.sort(key=lambda item: (-item["puntos_totales"], item["jugador_id"]))
    return {
        "equipos": teams, "numero_equipos": len(teams),
        "partidos_con_marcador": len(finished_ids),
        "anotadores": leaders,
        "plantillas_disponibles": sum(
            1 for team in teams if type(rosters.get(team["id"])) is dict),
        "aviso": "Solo estadísticas publicadas por FBM; las ausentes no se estiman.",
    }
