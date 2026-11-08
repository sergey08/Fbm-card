"""Contratos de formulario del registro/acceso observados en la APK Afición FBM.

Este módulo no inventa UID, token_push ni identificadores de dispositivo.
No hace peticiones y no almacena claves.
"""
from __future__ import annotations


def registration_fields(*, uid: str, plataforma: str,
                        tipo_dispositivo: str, version: str) -> dict[str, str]:
    """Formulario de Lc4/c;->b: accion=registrar."""
    if not all(isinstance(v, str) and v for v in
               (uid, plataforma, tipo_dispositivo, version)):
        raise ValueError("Faltan datos de dispositivo verificados")
    return {"accion": "registrar", "uid": uid, "plataforma": plataforma,
            "tipo_dispositivo": tipo_dispositivo, "version": version}


def access_fields(*, uid: str, token_push: str, id_dispositivo: str,
                  plataforma: str, tipo_dispositivo: str,
                  version: str) -> dict[str, str]:
    """Formulario de Lc4/c;->a: accion=acceso."""
    if not all(isinstance(v, str) for v in
               (uid, token_push, id_dispositivo, plataforma,
                tipo_dispositivo, version)):
        raise ValueError("Los campos deben ser cadenas")
    if not all((uid, id_dispositivo, plataforma, tipo_dispositivo, version)):
        raise ValueError("Faltan datos de dispositivo verificados")
    # token_push puede ser vacío en instalaciones sin notificaciones push.
    return {"accion": "acceso", "uid": uid, "token_push": token_push,
            "id_dispositivo": id_dispositivo, "plataforma": plataforma,
            "tipo_dispositivo": tipo_dispositivo, "version": version}
