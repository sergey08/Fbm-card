"""Cliente de consulta Afición FBM (solo origen observado en la APK).

No registra dispositivos ni fabrica identidades. Para hacer una búsqueda real
hay que aportar una identidad invitada obtenida de forma legítima.
"""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .guest_identity import GuestIdentity
from .guest_session import DeviceProfile, register_guest, access_guest
from .team_search import normalize_team_results

SEARCH_URL = "https://appaficionfbm.gesdeportiva.es/v2/busqueda.ashx"
MAX_RESPONSE_BYTES = 128 * 1024


class FBMAccessNotValidated(RuntimeError):
    """No se ha validado una sesión invitada completa."""


class FBMRequestError(RuntimeError):
    """La consulta no se pudo completar o validar."""


def _post_search(fields: dict[str, str]) -> dict[str, Any]:
    """Petición síncrona, diseñada para ejecutarse fuera del bucle de HA."""
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        SEARCH_URL, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "FBMCard-DEV/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status != 200:
                raise FBMRequestError(f"Respuesta HTTP {response.status}")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # No incluir en errores los campos de formulario ni la identidad.
        raise FBMRequestError("Error de conexión con Afición FBM") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise FBMRequestError("Respuesta FBM demasiado grande")
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise FBMRequestError("Respuesta FBM no es JSON válido") from exc
    if not isinstance(result, dict):
        raise FBMRequestError("Estructura de respuesta FBM inesperada")
    return result


class AficionFBMAdapter:
    """Búsquedas de clubes, categorías y equipos con identidad inyectada."""

    def __init__(self, identity: GuestIdentity | None = None):
        self._identity = identity

    @classmethod
    async def register_with_profile(cls, profile: DeviceProfile) -> "AficionFBMAdapter":
        """Registro explícito, solo con parámetros contrastados del APK."""
        return cls(await register_guest(profile))

    @classmethod
    async def access_with_profile(
        cls, profile: DeviceProfile, device_id: str
    ) -> "AficionFBMAdapter":
        """Recuperación explícita de una sesión de dispositivo existente."""
        return cls(await access_guest(profile, device_id))

    async def search(self, action: str, text: str, skip: int = 0) -> dict[str, Any]:
        if self._identity is None:
            raise FBMAccessNotValidated(
                "No hay identidad invitada validada; no se enviará tráfico"
            )
        fields = self._identity.search_fields(
            action, text, skip, datetime.now(timezone.utc)
        )
        return await asyncio.to_thread(_post_search, fields)

    async def search_teams(self, text: str, skip: int = 0) -> list[dict[str, str]]:
        """Normaliza equipos sin elegir automaticamente entre categorias o temporadas."""
        response = await self.search("buscarEquipo", text, skip)
        return normalize_team_results(response)

    async def query(self, kind: str, identifiers: dict) -> dict[str, Any]:
        """Conserva el bloqueo del contrato general hasta mapear sus consultas."""
        raise FBMAccessNotValidated(
            "La consulta general aún no tiene un contrato APK validado"
        )
