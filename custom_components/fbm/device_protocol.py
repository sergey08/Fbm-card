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


def extract_identity_fields(response: object) -> tuple[str, str]:
    """Extrae la identidad del DTO observado en el APK sin asumir éxito HTTP.

    Los nombres JSON aún requieren validación en una respuesta real. Por eso
    se rechazan respuestas ambiguas o incompletas, sin generar valores.
    """
    if not isinstance(response, dict):
        raise ValueError("La respuesta del dispositivo no es un objeto")
    if response.get("error") not in (None, "", False, 0):
        raise ValueError("El servidor comunicó un error de dispositivo")
    key = response.get("key")
    device_id = response.get("idDispositivo")
    if not isinstance(key, str) or not key:
        raise ValueError("No se ha recibido una clave de dispositivo válida")
    if not isinstance(device_id, str) or not device_id:
        raise ValueError("No se ha recibido un identificador de dispositivo válido")
    return key, device_id
