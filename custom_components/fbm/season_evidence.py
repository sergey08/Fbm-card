"""Conservative inspection of possible season IDs in a FBM phases payload.

Only explicitly allowlisted sports metadata is returned. This is diagnostic
evidence, NOT authorization to use a season identifier for persistence.
"""
from __future__ import annotations

CANDIDATE_KEYS = ("IdTemporada", "idTemporada", "id_temporada",
                  "idTemporadaActual", "IdTemporadaActual")


def _candidate(scope: str, obj: object) -> list[dict]:
    if not isinstance(obj, dict):
        return []
    found = []
    for key in CANDIDATE_KEYS:
        value = obj.get(key)
        if type(value) is int and value >= 0:
            found.append({"scope": scope, "field": key, "candidate": str(value)})
        elif isinstance(value, str) and 0 < len(value.strip()) <= 128:
            found.append({"scope": scope, "field": key, "candidate": value.strip()})
    return found


def inspect_season_evidence(response: object, phase_id: str, group_id: str) -> dict:
    """Inspect named nodes only, never dump raw payloads or opaque extras."""
    if not isinstance(response, dict) or response.get("error") != "":
        raise ValueError("Respuesta oficial no validada")
    phases = response.get("listaFasesGrupo")
    if not isinstance(phases, list):
        raise ValueError("Lista de fases no válida")
    selected = [x for x in phases if isinstance(x, dict) and x.get("IdFase") == phase_id]
    if len(selected) != 1:
        raise ValueError("Fase actual ambigua")
    groups = selected[0].get("Grupos")
    if not isinstance(groups, list):
        raise ValueError("Lista de grupos no válida")
    chosen = [x for x in groups if isinstance(x, dict) and x.get("IdGrupo") == group_id]
    if len(chosen) != 1:
        raise ValueError("Grupo actual ambiguo")
    candidates = (_candidate("response", response) +
                  _candidate("phase", selected[0]) +
                  _candidate("group", chosen[0]))
    distinct = {item["candidate"] for item in candidates}
    return {
        "season_candidates": candidates,
        "season_evidence_status": ("none" if not candidates else
                                   "conflicting" if len(distinct) > 1 else "unverified"),
        "season_verified": False,
    }
