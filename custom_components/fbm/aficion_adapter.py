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
from .team_roster import normalize_team_roster
from .player_protocol import players_fields, player_detail_fields
from .player_detail import post_player_detail_form, post_player_statistics_form, normalize_player_detail
from .player_statistics_bridge import PlayerStatisticsFetcher
from .device_protocol import open_request
from .team_phases import phase_options, classification_selection, current_phase_group
from .season_evidence import inspect_season_evidence
from .schedule_probe import summarize_schedule_shape
from .diagnostics import safe_error_category, safe_payload_shape

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
        if not fields["key"]:
            raise FBMAccessNotValidated("La clave de sesion requiere una nueva solicitud de acceso")
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

    def session_is_usable(self) -> bool:
        """Indica solo si existe clave dentro del plazo local observado."""
        return self._identity is not None and bool(self._identity.key_for_request(datetime.now(timezone.utc)))

    async def team_phase_options(self, team_id: str) -> dict:
        """Consulta opciones sin seleccionar rondas automaticamente."""
        device_id, key = self._team_key()
        response = await asyncio.to_thread(post_team_form, phases_fields(device_id, key, team_id))
        return phase_options(response)

    async def team_group_identity(self, team_id: str) -> dict:
        """Resolve phase/group IDs from FBM, without inferring season identifiers."""
        device_id, key = self._team_key()
        response = await asyncio.to_thread(
            post_team_form, phases_fields(device_id, key, team_id)
        )
        current = current_phase_group(response)
        selection = classification_selection(response)
        evidence = inspect_season_evidence(response, current["id_fase"], current["id_grupo"])
        return {
            **evidence,
            "team_id": team_id,
            "phase_id": current["id_fase"],
            "group_id": current["id_grupo"],
            "group_name": current["nombre_grupo"],
            "phase_name": current["nombre_fase"],
            "phase_type": selection["tipo_fase"],
            "season_id": None,
            "season_verified": False,
            "source": "FBM",
        }

    async def _team_schedule_response(self, team_id: str, start: date, end: date,
                                      round_id: str | None = None) -> dict:
        """One shared official request path for normal view and DEV probe."""
        if type(start) is not date or type(end) is not date or start > end or (end - start).days > 366:
            raise ValueError("Rango de fechas no valido")
        device_id, key = self._team_key()
        phase_response = await asyncio.to_thread(post_team_form, phases_fields(device_id, key, team_id))
        device_id, key = self._team_key()
        fields = schedule_fields(device_id, key, team_id, phase_response, start, end, round_id)
        return await asyncio.to_thread(post_team_form, fields)

    async def team_schedule(self, team_id: str, start: date, end: date,
                            round_id: str | None = None) -> dict:
        """Normalize the official schedule response for on-demand cards."""
        response = await self._team_schedule_response(team_id, start, end, round_id)
        return normalize_team_schedule(response)

    async def team_schedule_probe(self, team_id: str, start: date, end: date,
                                  round_id: str | None = None) -> dict:
        """Diagnostic: output only response structure, not teams, players or secrets."""
        response = await self._team_schedule_response(team_id, start, end, round_id)
        return summarize_schedule_shape(response)

    async def team_roster(self, team_id: str) -> dict:
        """APK LH5/j;->g: POST jugadores to /v2/equipo.ashx.

        This reuses the exact team transport and existing guest session.
        Only a verified normalized roster is returned; no raw response,
        photos, session key, or implicit following.
        """
        device_id, key = self._team_key()
        response = await asyncio.to_thread(
            post_team_form, players_fields(device_id, key, team_id)
        )
        return normalize_team_roster(response)

    async def team_roster_diagnostic(self, team_id: str) -> dict:
        """Observe only official response shape or a safe failure stage."""
        try:
            device_id, key = self._team_key()
        except Exception as exc:
            return {"ok": False, "stage": "session", "category": safe_error_category(exc)}
        try:
            fields = players_fields(device_id, key, team_id)
            response = await asyncio.to_thread(post_team_form, fields)
        except Exception as exc:
            return {"ok": False, "stage": "request", "category": safe_error_category(exc)}
        shape = safe_payload_shape(response, kind="roster")
        try:
            result = normalize_team_roster(response)
        except Exception as exc:
            return {"ok": False, "stage": "normalize", "category": safe_error_category(exc), "shape": shape}
        return {"ok": True, "stage": "complete", "shape": shape, "count": result["total"]}

    async def team_schedule_diagnostic(self, team_id: str, start: date, end: date) -> dict:
        """Identify failed phase, selection, fetch or parser without raw data."""
        try:
            device_id, key = self._team_key()
        except Exception as exc:
            return {"ok": False, "stage": "session", "category": safe_error_category(exc)}
        try:
            phase_response = await asyncio.to_thread(post_team_form, phases_fields(device_id, key, team_id))
        except Exception as exc:
            return {"ok": False, "stage": "phases_request", "category": safe_error_category(exc)}
        try:
            fields = schedule_fields(device_id, key, team_id, phase_response, start, end)
        except Exception as exc:
            return {
                "ok": False, "stage": "schedule_selection",
                "category": safe_error_category(exc),
                "phases_shape": safe_payload_shape(phase_response, kind="schedule"),
            }
        try:
            response = await asyncio.to_thread(post_team_form, fields)
        except Exception as exc:
            return {"ok": False, "stage": "schedule_request", "category": safe_error_category(exc)}
        shape = safe_payload_shape(response, kind="schedule")
        try:
            result = normalize_team_schedule(response)
        except Exception as exc:
            return {"ok": False, "stage": "normalize", "category": safe_error_category(exc), "shape": shape}
        return {"ok": True, "stage": "complete", "shape": shape, "count": len(result["partidos"])}

    async def player_detail(self, player_id: str) -> dict:
        """APK LH5/j;->e on-demand player detail using existing guest access."""
        device_id, key = self._team_key()
        response = await asyncio.to_thread(
            post_player_detail_form, player_detail_fields(device_id, key, player_id)
        )
        return normalize_player_detail(response, player_id)

    async def player_statistics(self, player_id: str, team_id: str) -> dict:
        """Use the same APK-verified session, context and stats transport.

        Raw player details remain private in this method and never enter
        HA cache, WebSocket results or logs.
        """
        device_id, key = self._team_key()

        async def raw_detail(target):
            return await asyncio.to_thread(
                post_player_detail_form,
                player_detail_fields(device_id, key, target),
            )

        async def post_stats(fields):
            return await asyncio.to_thread(post_player_statistics_form, fields)

        return await PlayerStatisticsFetcher(raw_detail, post_stats).fetch(
            player_id, team_id, device_id, key
        )

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
