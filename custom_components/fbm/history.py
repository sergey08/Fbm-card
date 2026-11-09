"""Historial local acotado para partidos validados de FBM.

No realiza peticiones de red. El adaptador autorizado debe entregar registros
normalizados mediante models.normalize_match antes de almacenarlos.
"""
from collections import deque
from copy import deepcopy
from datetime import datetime

MAX_MATCHES = 500
MAX_REVISIONS = 12


class FBMHistory:
    """Conservar versiones de cada partido, sin sobrescribir su evolución."""

    def __init__(self, max_matches=MAX_MATCHES, max_revisions=MAX_REVISIONS):
        if not (1 <= max_matches <= MAX_MATCHES and 1 <= max_revisions <= MAX_REVISIONS):
            raise ValueError("Límites de historial no válidos")
        self._max_matches = max_matches
        self._max_revisions = max_revisions
        self._matches = {}

    def record(self, match_id: str, match: dict) -> bool:
        """Añadir una revisión si ha cambiado el contenido deportivo.

        Se requiere identificador oficial estable. Devuelve True si se guardó.
        """
        if not isinstance(match_id, str) or not match_id.strip() or len(match_id) > 128:
            raise ValueError("Identificador de partido inválido")
        if not isinstance(match, dict):
            raise ValueError("El partido debe ser un objeto")
        required = {"local", "visitante", "state", "score", "source_url", "fetched_at"}
        if not required.issubset(match):
            raise ValueError("El partido debe estar normalizado")
        if not isinstance(match["fetched_at"], str):
            raise ValueError("Fecha de consulta inválida")
        try:
            stamp = datetime.fromisoformat(match["fetched_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Fecha de consulta inválida") from exc
        if stamp.tzinfo is None:
            raise ValueError("Se requiere fecha con zona horaria")

        key = match_id.strip()
        new = deepcopy(match)
        versions = self._matches.get(key)
        if versions:
            previous = versions[-1]
            if stamp < datetime.fromisoformat(previous["fetched_at"].replace("Z", "+00:00")):
                return False
            # El cambio de fetched_at no representa un nuevo resultado.
            comparable = lambda value: {k: v for k, v in value.items() if k != "fetched_at"}
            if comparable(previous) == comparable(new):
                return False
        elif len(self._matches) >= self._max_matches:
            # Orden de inserción: se elimina el partido más antiguo registrado.
            del self._matches[next(iter(self._matches))]
        if versions is None:
            versions = deque(maxlen=self._max_revisions)
            self._matches[key] = versions
        versions.append(new)
        return True

    def latest(self, match_id: str):
        """Obtener la última versión sin exponer el estado interno mutable."""
        versions = self._matches.get(match_id)
        return deepcopy(versions[-1]) if versions else None

    def revisions(self, match_id: str):
        """Devolver el historial acotado de un partido."""
        return deepcopy(list(self._matches.get(match_id, ())))

    def summary(self):
        """Datos pequeños y aptos para diagnósticos, sin historiales en sensores."""
        return {"matches": len(self._matches), "revisions": sum(len(v) for v in self._matches.values())}
