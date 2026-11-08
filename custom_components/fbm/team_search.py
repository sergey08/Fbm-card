"""Normalizacion de resultados de busqueda de equipos observados en FBM.

Los identificadores son opacos. No interpreta errores ni autentica respuestas.
"""
from __future__ import annotations


class TeamSearchError(ValueError):
    """La respuesta no permite construir una lista de seleccion segura."""


def normalize_team_results(response: object) -> list[dict[str, str]]:
    """Conserva los identificadores y desambiguadores para cualquier equipo."""
    if not isinstance(response, dict) or response.get("error") != "":
        raise TeamSearchError("Respuesta de busqueda ambigua o con error")
    teams = response.get("equipos")
    if not isinstance(teams, list):
        raise TeamSearchError("La respuesta no contiene una lista de equipos")
    fields = {"Id": "id", "Nombre": "nombre", "Club": "club",
              "Categoria": "categoria", "Temporada": "temporada"}
    results = []
    for team in teams:
        if not isinstance(team, dict):
            raise TeamSearchError("Elemento de equipo no valido")
        if any(not isinstance(team.get(name), str) or not team[name].strip()
               for name in fields):
            raise TeamSearchError("Equipo sin identificador o datos de seleccion")
        results.append({target: team[source] for source, target in fields.items()})
    return results
