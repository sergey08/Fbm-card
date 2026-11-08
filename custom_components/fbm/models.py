"""Contrato interno para datos deportivos obtenidos de fuentes oficiales FBM.

Este módulo NO consulta ninguna API y NO acredita que exista acceso a
resultados en directo. Valida la forma de los datos que entregará el adaptador.
"""
from datetime import datetime
from urllib.parse import urlsplit

OFFICIAL_HOSTS = frozenset({"fbm.es", "www.fbm.es", "appaficionfbm.gesdeportiva.es"})
MATCH_STATES = frozenset({"scheduled", "live", "finished", "postponed", "unknown"})


class FBMDataError(ValueError):
    """Datos ausentes, inconsistentes o procedentes de URL no permitida."""


def validate_official_url(url: str) -> str:
    """Admitir únicamente HTTPS en hosts oficiales expresamente conocidos."""
    if not isinstance(url, str):
        raise FBMDataError("La URL oficial debe ser texto")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise FBMDataError("URL oficial inválida") from exc
    if (
        parts.scheme != "https"
        or parts.hostname not in OFFICIAL_HOSTS
        or port not in (None, 443)
        or parts.username is not None
        or parts.password is not None
        or not parts.path.startswith("/")
    ):
        raise FBMDataError("Origen no incluido en la lista oficial permitida")
    return url


def normalize_match(record: dict, *, source_url: str, fetched_at: str) -> dict:
    """Normalizar un partido sin inferir marcador ni estado en directo.

    La URL y los valores los proporciona un adaptador FBM previamente validado.
    El resultado no constituye prueba de autenticidad de la respuesta.
    """
    validate_official_url(source_url)
    if not isinstance(record, dict):
        raise FBMDataError("El partido debe ser un objeto")
    try:
        datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise FBMDataError("fetched_at debe ser ISO 8601") from exc
    state = record.get("state", "unknown")
    if state not in MATCH_STATES:
        raise FBMDataError("Estado del partido desconocido")
    local = record.get("local")
    visitor = record.get("visitante")
    if not all(isinstance(x, str) and x.strip() for x in (local, visitor)):
        raise FBMDataError("Faltan nombres de equipos")
    score = record.get("score")
    if score is not None:
        if not isinstance(score, dict) or set(score) != {"local", "visitante"}:
            raise FBMDataError("Marcador incompleto")
        if any(type(score[k]) is not int or score[k] < 0 for k in ("local", "visitante")):
            raise FBMDataError("Marcador no válido")
    return {
        "local": local.strip(),
        "visitante": visitor.strip(),
        "state": state,
        "score": score,
        "period": record.get("period") if state == "live" else None,
        "source_url": source_url,
        "fetched_at": fetched_at,
        "source_updated_at": record.get("source_updated_at"),
    }
