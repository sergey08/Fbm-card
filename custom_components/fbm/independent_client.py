"""Orquestacion explicita de identidad independiente y consultas FBM."""
from __future__ import annotations

import asyncio
from datetime import date

from .aficion_adapter import AficionFBMAdapter, FBMAccessNotValidated
from .guest_session import DeviceProfile
from .independent_identity import IdentityError
from .device_protocol import post_device_form, registration_fields, extract_identity_fields
from .query_cache import QueryCache


class IndependentClient:
    """Mantiene sesiones en memoria; no registra ni realiza trafico al crearse."""

    def __init__(self, identity_store, *, recovery_store=None):
        self._store = identity_store
        self._recovery_store = recovery_store
        self._adapter = None
        self._lock = asyncio.Lock()
        self._cache = QueryCache(ttl_seconds=300, max_entries=128)

    async def async_create_identity(self) -> None:
        """Crea una identidad persistente cuando se solicita expresamente."""
        async with self._lock:
            await self._store.async_create()
            self._adapter = None
            self._cache.clear()

    async def async_status(self) -> dict[str, bool]:
        """Estado sin credenciales ni identificadores."""
        async with self._lock:
            identity = await self._store.async_load()
            return {"identidad_creada": identity is not None,
                    "candidato_guardado": bool(identity and identity.candidate_device_id),
                    "registro_pendiente": bool(identity and identity.registration_state == "pending"),
                    "sesion_en_memoria": self._adapter is not None,
                    "sesion_vigente": bool(self._adapter and self._adapter.session_is_usable())}

    async def async_bind_candidate(self, candidate_device_id: str) -> None:
        """Vincula un candidato proporcionado por un flujo de provision explicito."""
        async with self._lock:
            identity = await self._store.async_load()
            if identity is None:
                raise IdentityError("No existe una identidad local")
            await self._store.async_bind_candidate(identity.uid, candidate_device_id)
            self._adapter = None
            self._cache.clear()

    async def async_register(self, android_release: str) -> None:
        """Solicita un registro experimental solo cuando se llama explicitamente."""
        if not isinstance(android_release, str) or not android_release.strip():
            raise ValueError("Se requiere una version de perfil Android")
        async with self._lock:
            identity = await self._store.async_begin_registration()
            await self._registration_request(identity, android_release, allow_duplicate=False)

    async def async_recover_registration(self, android_release: str) -> None:
        """Reintento de recuperacion expresamente solicitado, nunca automatico."""
        if not isinstance(android_release, str) or not android_release.strip():
            raise ValueError("Se requiere una version de perfil Android")
        async with self._lock:
            identity = await self._store.async_load()
            if identity is None or identity.registration_state != "pending" or identity.candidate_device_id is not None:
                raise IdentityError("No hay un registro pendiente de recuperar")
            await self._registration_request(identity, android_release, allow_duplicate=True)

    async def _registration_request(self, identity, android_release, *, allow_duplicate):
        form = registration_fields(uid=identity.uid, plataforma="Android " + android_release.strip(),
                                   tipo_dispositivo="mobile", version="5.0.42")
        response = await asyncio.to_thread(post_device_form, form)
        try:
            _, device_id = extract_identity_fields(response, allow_duplicate=allow_duplicate)
        except ValueError as exc:
            raise IdentityError("Registro no validado; no se guardo un candidato") from None
        await self._store.async_bind_candidate(identity.uid, device_id)
        self._adapter = None
        self._cache.clear()

    async def async_connect(self, android_release: str) -> None:
        """Solicita acceso cuando se indica expresamente; no registra dispositivos."""
        if not isinstance(android_release, str) or not android_release.strip():
            raise ValueError("Se requiere una version de perfil Android")
        async with self._lock:
            self._adapter = None
            self._cache.clear()
            identity = await self._store.async_load()
            if identity is None or not identity.candidate_device_id:
                raise IdentityError("Falta una identidad con candidato de dispositivo")
            profile = DeviceProfile(uid=identity.uid, plataforma="Android " + android_release.strip(),
                                    tipo_dispositivo="mobile", version="5.0.42")
            self._adapter = await AficionFBMAdapter.access_with_profile(profile, identity.candidate_device_id)
            # Save only the Android release, never UID, token or device identity.
            # A failure here must not invalidate a successful connection.
            if self._recovery_store is not None:
                try:
                    await self._recovery_store.async_save({"format": 1, "android_release": android_release.strip()})
                except Exception:
                    pass

    async def async_restore(self) -> bool:
        """Restore existing device access only; never create/register identities.

        No stored Android release means no automatic traffic. Access failures
        are nonfatal; the next explicit connect remains available.
        """
        if self._recovery_store is None:
            return False
        try:
            saved = await self._recovery_store.async_load()
            if not isinstance(saved, dict) or set(saved) != {"format", "android_release"} or saved["format"] != 1:
                return False
            release = saved["android_release"]
            if not isinstance(release, str) or not release.strip() or len(release) > 32:
                return False
            await self.async_connect(release)
            return True
        except Exception:
            return False

    async def async_disconnect(self) -> None:
        """Olvida la sesion en memoria sin eliminar la identidad persistida."""
        async with self._lock:
            self._adapter = None
            self._cache.clear()

    async def _cached_query(self, key, operation, *, ttl):
        """Serializa consultas y conserva solo resultados normalizados en memoria."""
        async with self._lock:
            adapter = self._adapter
            if adapter is None or not adapter.session_is_usable():
                raise FBMAccessNotValidated("Se requiere una conexion explicita vigente")
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            result = await operation(adapter)
            self._cache.put(key, result, ttl_seconds=ttl)
            return result

    async def async_search_teams(self, text: str, skip: int = 0) -> list[dict[str, str]]:
        if not isinstance(text, str) or not text.strip() or len(text) > 100 or type(skip) is not int or not 0 <= skip <= 10000:
            raise ValueError("Busqueda no valida")
        return await self._cached_query(("equipos", text, skip), lambda adapter: adapter.search_teams(text, skip), ttl=300)

    async def async_team_phase_options(self, team_id: str) -> dict:
        self._validate_team_id(team_id)
        return await self._cached_query(("fases", team_id), lambda adapter: adapter.team_phase_options(team_id), ttl=300)

    async def async_team_schedule(self, team_id: str, start: date, end: date, round_id: str | None = None) -> dict:
        self._validate_team_id(team_id)
        if type(start) is not date or type(end) is not date or start > end or (end - start).days > 366:
            raise ValueError("Rango de fechas no valido")
        if round_id is not None:
            self._validate_team_id(round_id)
        async def query(adapter):
            if round_id is None:
                return await adapter.team_schedule(team_id, start, end)
            return await adapter.team_schedule(team_id, start, end, round_id)
        return await self._cached_query(("horarios", team_id, start.isoformat(), end.isoformat(), round_id or ""), query, ttl=60)

    async def async_team_schedule_probe(self, team_id: str, start: date, end: date,
                                        round_id: str | None = None) -> dict:
        """Explicit DEV-only diagnostic, never caches personal match data."""
        self._validate_team_id(team_id)
        if type(start) is not date or type(end) is not date or start > end or (end - start).days > 366:
            raise ValueError("Rango de fechas no valido")
        if round_id is not None:
            self._validate_team_id(round_id)
        async with self._lock:
            if self._adapter is None or not self._adapter.session_is_usable():
                raise FBMAccessNotValidated("Se requiere sesión FBM vigente")
            return await self._adapter.team_schedule_probe(team_id, start, end, round_id)

    async def async_team_group_identity(self, team_id: str) -> dict:
        """Read official current group; do not enable follow or infer season."""
        self._validate_team_id(team_id)
        # No query cache here: this verification must never look fresher
        # than it is, particularly before enabling persistent following.
        async with self._lock:
            if self._adapter is None or not self._adapter.session_is_usable():
                raise FBMAccessNotValidated("Se requiere sesión FBM vigente")
            return await self._adapter.team_group_identity(team_id)

    async def async_team_roster(self, team_id: str) -> dict:
        """On-demand roster; same adapter to be used for opt-in group syncing."""
        self._validate_team_id(team_id)
        return await self._cached_query(
            ("plantilla", team_id),
            lambda adapter: adapter.team_roster(team_id),
            ttl=120,
        )

    async def async_player_detail(self, player_id: str) -> dict:
        """Detail is queried only on explicit request; no implicit follow."""
        self._validate_team_id(player_id)
        return await self._cached_query(
            ("jugador", player_id), lambda adapter: adapter.player_detail(player_id),
            ttl=120,
        )

    async def async_team_standings(self, team_id: str) -> dict:
        self._validate_team_id(team_id)
        return await self._cached_query(("clasificacion", team_id), lambda adapter: adapter.team_standings(team_id), ttl=120)

    @staticmethod
    def _validate_team_id(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 512:
            raise ValueError("Identificador deportivo no valido")
