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


def extract_identity_fields(response: object, *, allow_duplicate: bool = False) -> tuple[str, str]:
    """Valida el contrato conservador del registro invitado experimental.

    El esquema de exito no se ha corroborado con un alta real. No se
    aceptan alias de campos ni valores de error ambiguos.
    """
    if not isinstance(response, dict):
        raise ValueError("La respuesta de registro no es un objeto")
    allowed_errors = ("", "uuid ya registrado") if allow_duplicate else ("",)
    error = response.get("error")
    if not isinstance(error, str) or error not in allowed_errors:
        raise ValueError("Registro de dispositivo no validado")
    key = response.get("key")
    device_id = response.get("id_dispositivo")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("No se ha recibido una clave valida")
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("No se ha recibido un identificador valido")
    return key, device_id


def extract_access_identity_fields(response: object, expected_device_id: str) -> tuple[str, str]:
    """Interpreta el acceso observado conservando el ID conocido si viene vacio.

    Solo acepta el error vacio observado; rechaza respuestas ambiguas y IDs distintos.
    La validez de la sesion se debe comprobar mediante una consulta posterior.
    """
    if not isinstance(expected_device_id, str) or not expected_device_id.strip():
        raise ValueError("Falta identificador de dispositivo conocido")
    if not isinstance(response, dict) or response.get("error") != "":
        raise ValueError("Respuesta de acceso ambigua o con error")
    key, received_id = response.get("key"), response.get("id_dispositivo")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Falta clave de acceso")
    if not isinstance(received_id, str) or received_id not in ("", expected_device_id):
        raise ValueError("Identificador de acceso inconsistente")
    return key, expected_device_id


DEVICE_URL = "https://appaficionfbm.gesdeportiva.es/dispositivo.ashx"


class DeviceTransportError(RuntimeError):
    """Fallo clasificado sin datos de la solicitud ni de la respuesta."""

    def __init__(self, category: str, status: int | None = None):
        super().__init__(category)
        self.category = category
        self.status = status


def open_request(request, *, timeout):
    """Abre sin seguir redirecciones que puedan reenviar identificadores o claves."""
    import urllib.request

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    return urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout)


def post_device_form(fields: dict[str, str], *, timeout: int = 12) -> dict:
    """Transporta un formulario explícito; no genera UID ni inicia registro solo.

    No se registran valores ni cuerpos de respuesta en los mensajes de error.
    Se ejecuta en un hilo cuando se llama desde Home Assistant.
    """
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    allowed = {
        "registrar": {"accion", "uid", "plataforma", "tipo_dispositivo", "version"},
        "acceso": {"accion", "uid", "token_push", "id_dispositivo",
                   "plataforma", "tipo_dispositivo", "version"},
    }
    action = fields.get("accion")
    if action not in allowed:
        raise ValueError("Operación de dispositivo no permitida")
    if set(fields) != allowed[action]:
        raise ValueError("Campos de dispositivo inesperados o incompletos")
    if not all(isinstance(value, str) for value in fields.values()):
        raise ValueError("Los campos de dispositivo deben ser cadenas")
    required = allowed[action] - {"accion", "token_push"}
    if any(not fields[name] for name in required):
        raise ValueError("Faltan campos obligatorios de dispositivo")
    body = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        DEVICE_URL, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "FBMCard-DEV/0.1"},
    )
    try:
        with open_request(request, timeout=timeout) as response:
            if response.status != 200:
                raise DeviceTransportError("http", response.status)
            raw = response.read(131073)
    except urllib.error.HTTPError as exc:
        raise DeviceTransportError("http", exc.code) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise DeviceTransportError("conexion") from None
    if len(raw) > 131072:
        raise DeviceTransportError("respuesta_grande")
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise DeviceTransportError("json_invalido") from None
    if not isinstance(data, dict):
        raise DeviceTransportError("json_no_objeto")
    return data
