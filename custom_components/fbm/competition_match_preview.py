"""Read-only match preview derived exclusively from archived FBM snapshots.

No network access, no player information and no inferred missing scores.
"""
from __future__ import annotations

from datetime import datetime


def _date(match):
    value = match.get("fecha")
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        return None


def _finished(match):
    score = match.get("marcador")
    return (match.get("estado") == "finished" and isinstance(score, dict)
            and type(score.get("local")) is int
            and type(score.get("visitante")) is int)


def match_preview(standings, fixtures, team_name):
    """Summarize the next fixture and two teams' last four scored games.

    Missing dates, venue and scores stay missing; snapshots are not mutated.
    """
    rows = standings.get("clasificacion", [])
    games = fixtures.get("partidos", [])
    if (not isinstance(rows, list) or len(rows) > 100
            or not isinstance(games, list) or len(games) > 2000
            or not isinstance(team_name, str) or not team_name.strip()
            or len(team_name) > 512):
        raise ValueError("Invalid archive data")
    lookup = {row["equipo"]: row for row in rows
              if isinstance(row, dict) and isinstance(row.get("equipo"), str)}
    if team_name not in lookup:
        raise ValueError("Team not in standings")
    scheduled = [game for game in games if isinstance(game, dict)
                 and team_name in (game.get("local"), game.get("visitante"))
                 and game.get("estado") == "scheduled" and _date(game) is not None]
    scheduled.sort(key=lambda game: (_date(game), game.get("hora") or ""))
    upcoming = scheduled[0] if scheduled else None
    rival = None
    if upcoming:
        rival = upcoming["visitante"] if upcoming.get("local") == team_name else upcoming.get("local")
    def recent(name):
        if not name:
            return []
        matches = [game for game in games if isinstance(game, dict)
                   and name in (game.get("local"), game.get("visitante"))
                   and _finished(game) and _date(game) is not None]
        matches.sort(key=lambda game: (_date(game), game.get("hora") or ""), reverse=True)
        return [{"fecha": game.get("fecha"), "jornada": game.get("jornada"),
                 "local": game.get("local"), "visitante": game.get("visitante"),
                 "marcador": game.get("marcador")} for game in matches[:4]]
    prior = [game for game in games if isinstance(game, dict)
             and rival and {game.get("local"), game.get("visitante")} == {team_name, rival}
             and _finished(game)]
    return {
        "equipo": team_name,
        "rival": rival,
        "proximo_partido": ({key: upcoming.get(key) for key in
                             ("fecha", "hora", "jornada", "local", "visitante", "campo", "direccion")}
                            if upcoming else None),
        "clasificacion": {
            team_name: lookup[team_name],
            **({rival: lookup[rival]} if rival in lookup else {}),
        },
        "ultimos_cuatro": {team_name: recent(team_name),
                           **({rival: recent(rival)} if rival else {})},
        "enfrentamientos_previos": [
            {"fecha": game.get("fecha"), "local": game.get("local"),
             "visitante": game.get("visitante"), "marcador": game.get("marcador")}
            for game in sorted(prior, key=lambda game: _date(game) or datetime.min.date(),
                               reverse=True)[:4]
        ],
        "cobertura": {"partidos_archivados": len(games),
                       "partidos_con_marcador": sum(_finished(game) for game in games
                                                    if isinstance(game, dict))},
    }
