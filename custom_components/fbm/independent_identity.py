"""Identidad independiente persistida bajo demanda; no realiza peticiones."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import re
import secrets


class IdentityError(ValueError):
    """Identidad ausente, corrupta o incompatible."""


@dataclass(frozen=True)
class IndependentIdentity:
    uid: str = field(repr=False)
    candidate_device_id: str | None = field(default=None, repr=False)


def _decode(data: object) -> IndependentIdentity:
    if not isinstance(data, dict) or set(data) != {"format", "uid", "candidate_device_id"}:
        raise IdentityError("Estructura de identidad no valida")
    uid, device_id = data["uid"], data["candidate_device_id"]
    if (type(data["format"]) is not int or data["format"] != 1 or not isinstance(uid, str)
            or not re.fullmatch(r"[0-9a-f]{16}", uid)
            or (device_id is not None and (not isinstance(device_id, str) or not device_id.strip()))):
        raise IdentityError("Identidad almacenada no valida")
    return IndependentIdentity(uid, device_id)


class IndependentIdentityStore:
    """Gestiona un unico registro mediante un almacen asincrono inyectado.

    La creacion y vinculacion se invocan explicitamente; no hay trafico de red.
    Las claves de sesion nunca se almacenan. Un solo gestor debe ser propietario
    del mismo almacen en cada proceso.
    """

    def __init__(self, store, *, async_exists=None):
        self._store = store
        self._lock = asyncio.Lock()
        self._async_exists = async_exists
        self._ambiguous_storage = False

    async def _load_checked(self):
        existed = await self._async_exists() if self._async_exists is not None else False
        data = await self._store.async_load()
        # HA Store puede conservar una copia corrupta y devolver None: no crear
        # una identidad diferente en el mismo proceso tras detectar ese caso.
        if existed and data is None:
            self._ambiguous_storage = True
            raise IdentityError("Almacen previo ilegible; requiere recuperacion")
        return data

    async def async_load(self) -> IndependentIdentity | None:
        async with self._lock:
            data = await self._load_checked()
            return None if data is None else _decode(data)

    async def async_create(self) -> IndependentIdentity:
        """Crea identidad aleatoria solo si no existe un registro previo."""
        async with self._lock:
            if self._ambiguous_storage or await self._load_checked() is not None:
                raise IdentityError("Ya existe una identidad; no se reemplazara")
            identity = IndependentIdentity(uid=secrets.token_hex(8))
            await self._store.async_save({"format": 1, "uid": identity.uid, "candidate_device_id": None})
            return identity

    async def async_bind_candidate(self, uid: str, device_id: str) -> IndependentIdentity:
        """Guarda un candidato sin reemplazar un identificador distinto."""
        if not isinstance(device_id, str) or not device_id.strip():
            raise IdentityError("Identificador candidato no valido")
        async with self._lock:
            data = await self._load_checked()
            if data is None:
                raise IdentityError("No existe una identidad local")
            identity = _decode(data)
            if uid != identity.uid:
                raise IdentityError("La identidad no corresponde al candidato")
            if identity.candidate_device_id not in (None, device_id):
                raise IdentityError("Ya existe un candidato diferente")
            if identity.candidate_device_id is None:
                await self._store.async_save({"format": 1, "uid": identity.uid, "candidate_device_id": device_id})
            return IndependentIdentity(identity.uid, device_id)
