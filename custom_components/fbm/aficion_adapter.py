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
from datetime import date, datetime, timezone
from typing import Any

from .guest_identity import GuestIdentity
from .guest_session import DeviceProfile, register_guest, access_guest
from .team_search import normalize_team_results
from .team_protocol import phases_fields, schedule_fields, standings_fields, post_team_form
from .team_schedule import normalize_team_schedule
from .team_standings import normalize_standings
from .device_protocol import open_request
from .team_phases import phase_options

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
        with open_request(req, timeout=12) as response:
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

    def _team_key(self) -> tuple[str, str]:
        if self._identity is None:
            raise FBMAccessNotValidated("No hay identidad para consultar equipos")
        key = self._identity.key_for_request(datetime.now(timezone.utc))
        if not key:
            raise FBMAccessNotValidated("La clave de sesion requiere una nueva solicitud de acceso")
        return self._identity.device_id, key

    async def team_phase_options(self, team_id: str) -> dict:
        """Consulta opciones sin seleccionar rondas automaticamente."""
        device_id, key = self._team_key()
        response = await asyncio.to_thread(post_team_form, phases_fields(device_id, key, team_id))
        return phase_options(response)

    async def team_schedule(self, team_id: str, start: date, end: date, round_id: str | None = None) -> dict:
        """Consulta fases y horarios bajo demanda; no registra ni renueva sesiones."""
        if type(start) is not date or type(end) is not date or start > end or (end - start).days > 366:
            raise ValueError("Rango de fechas no valido")
        device_id, key = self._team_key()
        phase_response = await asyncio.to_thread(post_team_form, phases_fields(device_id, key, team_id))
        device_id, key = self._team_key()
        fields = schedule_fields(device_id, key, team_id, phase_response, start, end, round_id)
        response = await asyncio.to_thread(post_team_form, fields)
        return normalize_team_schedule(response)

    async def team_standings(self, team_id: str) -> dict:
        """Consulta la clasificacion del grupo actual del equipo elegido."""
        device_id, key = self._team_key()
        phases = await asyncio.to_thread(post_team_form, phases_fields(device_id, key, team_id))
        device_id, key = self._team_key()
        fields = standings_fields(device_id, key, phases)
        response = await asyncio.to_thread(post_team_form, fields)
        return normalize_standings(response)

    async def query(self, kind: str, identifiers: dict) -> dict[str, Any]:
        """Conserva el bloqueo del contrato general hasta mapear sus consultas."""
        raise FBMAccessNotValidated(
            "La consulta general aún no tiene un contrato APK validado"
        )
