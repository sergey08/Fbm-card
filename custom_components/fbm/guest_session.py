"""Flujo explícito de registro invitado FBM.

El UID y los valores de plataforma deben proceder de la aplicación/protocolo
validado, nunca de valores generados arbitrariamente por esta biblioteca.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from .device_protocol import (
    registration_fields, access_fields, post_device_form, extract_identity_fields,
    extract_access_identity_fields
)
from .guest_identity import GuestIdentity


@dataclass(frozen=True)
class DeviceProfile:
    uid: str = field(repr=False)
    plataforma: str
    tipo_dispositivo: str
    version: str
    token_push: str = field(default="", repr=False)

    @classmethod
    def from_android_phone(
        cls, *, android_id: str, android_release: str, token_push: str = ""
    ) -> "DeviceProfile":
        """Perfil observado en la ruta PHONE de la APK 5.0.42.

        android_id debe obtenerse de un dispositivo autorizado. No se genera
        ni se solicita automáticamente un identificador.
        """
        if not isinstance(android_id, str) or not android_id.strip():
            raise ValueError("Se requiere Android ID real del dispositivo")
        if not isinstance(android_release, str) or not android_release.strip():
            raise ValueError("Se requiere versión Android real del dispositivo")
        return cls(
            uid=android_id.strip(),
            plataforma="Android " + android_release.strip(),
            tipo_dispositivo="mobile",
            version="5.0.42",
            token_push=token_push,
        )

    def __post_init__(self):
        if not all(isinstance(x, str) and x for x in (
            self.uid, self.plataforma, self.tipo_dispositivo, self.version
        )):
            raise ValueError("El perfil requiere UID y plataforma reales")
        if not isinstance(self.token_push, str):
            raise ValueError("token_push debe ser una cadena")


async def register_guest(profile: DeviceProfile) -> GuestIdentity:
    """Registro bajo demanda: no se ejecuta durante la importación."""
    response = await asyncio.to_thread(
        post_device_form,
        registration_fields(
            uid=profile.uid, plataforma=profile.plataforma,
            tipo_dispositivo=profile.tipo_dispositivo, version=profile.version
        ),
    )
    key, device_id = extract_identity_fields(response)
    return GuestIdentity.from_response(key, device_id, datetime.now(timezone.utc))


async def access_guest(profile: DeviceProfile, device_id: str) -> GuestIdentity:
    """Acceso de un dispositivo ya registrado, sin inventar su identificador."""
    response = await asyncio.to_thread(
        post_device_form,
        access_fields(
            uid=profile.uid, token_push=profile.token_push,
            id_dispositivo=device_id, plataforma=profile.plataforma,
            tipo_dispositivo=profile.tipo_dispositivo, version=profile.version
        ),
    )
    key, response_device_id = extract_access_identity_fields(response, device_id)
    return GuestIdentity.from_response(
        key, response_device_id, datetime.now(timezone.utc)
    )
