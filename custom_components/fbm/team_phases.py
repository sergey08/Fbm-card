"""Seleccion de fase y grupo a partir del contrato de respuesta observado."""
from __future__ import annotations


class TeamPhasesError(ValueError):
    """La respuesta no identifica una fase y un grupo de forma inequivoca."""


def phase_options(response: object) -> dict:
    """Expone opciones de la fase actual sin elegir una ronda por defecto."""
    if not isinstance(response, dict) or response.get("error") != "":
        raise TeamPhasesError("Respuesta ambigua o con error")
    phase_id, phases = response.get("faseActual"), response.get("listaFasesGrupo")
    if not isinstance(phase_id, str) or not phase_id.strip() or not isinstance(phases, list):
        raise TeamPhasesError("Falta fase actual")
    matches = [p for p in phases if isinstance(p, dict) and p.get("IdFase") == phase_id]
    if len(matches) != 1:
        raise TeamPhasesError("La fase actual no es unica")
    phase = matches[0]
    name, rounds = phase.get("NombreFase"), phase.get("Rondas")
    if not isinstance(name, str) or not name.strip() or not isinstance(rounds, list):
        raise TeamPhasesError("Fase o rondas invalidas")
    choices, ids = [], set()
    for item in rounds:
        if not isinstance(item, dict):
            raise TeamPhasesError("Ronda invalida")
        rid, rname = item.get("IdRonda"), item.get("NombreRonda")
        if not isinstance(rid, str) or not rid.strip() or not isinstance(rname, str) or not rname.strip() or rid in ids:
            raise TeamPhasesError("Ronda incompleta o duplicada")
        ids.add(rid)
        choices.append({"id": rid, "nombre": rname})
    return {"id_fase": phase_id, "nombre_fase": name, "rondas": choices}


def schedule_selection(response: object, round_id: str | None = None) -> dict:
    """Selecciona grupo actual o una ronda elegida explicitamente."""
    options = phase_options(response)
    if options["rondas"]:
        if not isinstance(round_id, str) or not round_id.strip():
            raise TeamPhasesError("Selecciona una ronda")
        matches = [r for r in options["rondas"] if r["id"] == round_id]
        if len(matches) != 1:
            raise TeamPhasesError("Ronda no disponible")
        return {"id_fase": options["id_fase"], "id_grupo": "", "id_ronda": round_id}
    if round_id is not None:
        raise TeamPhasesError("La fase no tiene rondas")
    current = current_phase_group(response)
    return {"id_fase": current["id_fase"], "id_grupo": current["id_grupo"], "id_ronda": ""}


def current_phase_group(response: object) -> dict:
    """Selecciona por identificadores, sin suponer orden ni nombres concretos."""
    if not isinstance(response, dict) or response.get("error") != "":
        raise TeamPhasesError("Respuesta ambigua o con error")
    phase_id, group_id = response.get("faseActual"), response.get("grupoActual")
    phases = response.get("listaFasesGrupo")
    if (not isinstance(phase_id, str) or not phase_id.strip()
            or not isinstance(group_id, str) or not group_id.strip()
            or not isinstance(phases, list)):
        raise TeamPhasesError("Faltan fase o grupo actuales")
    matches = [item for item in phases if isinstance(item, dict) and item.get("IdFase") == phase_id]
    if len(matches) != 1:
        raise TeamPhasesError("La fase actual no es unica")
    phase = matches[0]
    groups = phase.get("Grupos")
    rounds = phase.get("Rondas")
    if not isinstance(groups, list) or not isinstance(rounds, list):
        raise TeamPhasesError("Listas de grupos o rondas invalidas")
    matches = [item for item in groups if isinstance(item, dict) and item.get("IdGrupo") == group_id]
    if len(matches) != 1:
        raise TeamPhasesError("El grupo actual no es unico")
    name, group_name = phase.get("NombreFase"), matches[0].get("NombreGrupo")
    if not isinstance(name, str) or not name.strip() or not isinstance(group_name, str) or not group_name.strip():
        raise TeamPhasesError("Faltan nombres de fase o grupo")
    return {"id_fase": phase_id, "nombre_fase": name, "id_grupo": group_id,
            "nombre_grupo": group_name, "rondas": list(rounds)}
