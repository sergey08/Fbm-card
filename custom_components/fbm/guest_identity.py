"""Gestión local del plazo de uso de la clave observado en la APK Afición FBM.

No autentica, no hace solicitudes HTTP y no interpreta el plazo como
caducidad confirmada por el servidor.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

KEY_WINDOW_MS = 84_400_000


def utc_epoch_ms(now: datetime) -> int:
    """Milisegundos Unix UTC; exige un datetime con zona horaria."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Se requiere una fecha con zona horaria")
    return int(now.timestamp() * 1000)


@dataclass(frozen=True)
class GuestIdentity:
    """Identidad obtenida legítimamente de una respuesta de dispositivo."""
    key: str
    device_id: str
    key_until_ms: int

    @classmethod
    def from_response(cls, key: str, device_id: str, now: datetime) -> "GuestIdentity":
        return cls(key=key, device_id=device_id,
                   key_until_ms=utc_epoch_ms(now) + KEY_WINDOW_MS)

    def key_for_request(self, now: datetime) -> str:
        """La APK usa key si la hora actual es estrictamente menor al límite."""
        return self.key if utc_epoch_ms(now) < self.key_until_ms else ""

    def search_fields(self, action: str, text: str, skip: int, now: datetime) -> dict[str, str]:
        """Cinco campos observados; no realiza solicitudes ni valida el endpoint."""
        if action not in {"buscarClub", "buscarCategoria", "buscarEquipo"}:
            raise ValueError("Acción no verificada")
        if skip < 0:
            raise ValueError("skip no puede ser negativo")
        return {"accion": action, "id_dispositivo": self.device_id,
                "key": self.key_for_request(now), "texto": text, "skip": str(skip)}
