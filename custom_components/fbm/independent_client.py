"""Orquestacion explicita de identidad independiente y consultas FBM."""
from __future__ import annotations

import asyncio
from datetime import date

from .aficion_adapter import AficionFBMAdapter, FBMAccessNotValidated
from .guest_session import DeviceProfile
from .independent_identity import IdentityError


class IndependentClient:
    """Mantiene sesiones en memoria; no registra ni realiza trafico al crearse."""

    def __init__(self, identity_store):
        self._store = identity_store
        self._adapter = None
        self._lock = asyncio.Lock()

    async def async_create_identity(self) -> None:
        """Crea una identidad persistente cuando se solicita expresamente."""
        async with self._lock:
            await self._store.async_create()

    async def async_bind_candidate(self, candidate_device_id: str) -> None:
        """Vincula un candidato proporcionado por un flujo de provision explicito."""
        async with self._lock:
            identity = await self._store.async_load()
            if identity is None:
                raise IdentityError("No existe una identidad local")
            await self._store.async_bind_candidate(identity.uid, candidate_device_id)
            self._adapter = None

    async def async_connect(self, android_release: str) -> None:
        """Solicita acceso cuando se indica expresamente; no registra dispositivos."""
        if not isinstance(android_release, str) or not android_release.strip():
            raise ValueError("Se requiere una version de perfil Android")
        async with self._lock:
            self._adapter = None
            identity = await self._store.async_load()
            if identity is None or not identity.candidate_device_id:
                raise IdentityError("Falta una identidad con candidato de dispositivo")
            profile = DeviceProfile(uid=identity.uid, plataforma="Android " + android_release.strip(),
                                    tipo_dispositivo="mobile", version="5.0.42")
            self._adapter = await AficionFBMAdapter.access_with_profile(profile, identity.candidate_device_id)

    async def async_disconnect(self) -> None:
        """Olvida la sesion en memoria sin eliminar la identidad persistida."""
        async with self._lock:
            self._adapter = None

    async def async_search_teams(self, text: str, skip: int = 0) -> list[dict[str, str]]:
        adapter = self._adapter
        if adapter is None:
            raise FBMAccessNotValidated("Se requiere una conexion explicita")
        return await adapter.search_teams(text, skip)

    async def async_team_schedule(self, team_id: str, start: date, end: date) -> dict:
        adapter = self._adapter
        if adapter is None:
            raise FBMAccessNotValidated("Se requiere una conexion explicita")
        return await adapter.team_schedule(team_id, start, end)
