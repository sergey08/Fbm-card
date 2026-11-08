#!/usr/bin/env python3
"""Diagnóstico de registro FBM: sin tráfico por defecto y sin mostrar secretos.

Uso:
  python scripts/probar_registro_invitado.py --android-release 16
  FBM_ANDROID_ID=... python scripts/probar_registro_invitado.py --android-release 16 --enviar

No supone que el ANDROID_ID visible por adb shell sea el de Afición FBM.
Una prueba de registro independiente requiere un identificador propio y autorizado.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from custom_components.fbm.device_protocol import (  # noqa: E402
    registration_fields, post_device_form, extract_identity_fields
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-release", required=True,
                        help="Versión real del Android de prueba, p. ej. 16")
    parser.add_argument("--enviar", action="store_true",
                        help="Autoriza explícitamente un único POST de registro")
    args = parser.parse_args(argv)

    if not args.android_release.strip():
        parser.error("La versión de Android no puede estar vacía")
    if not args.enviar:
        print("SIN RED: formulario previsto: accion=registrar, uid=<privado>, "
              "plataforma=Android <versión>, tipo_dispositivo=mobile, version=5.0.42")
        print("Para enviar, aporte FBM_ANDROID_ID por variable de entorno y --enviar.")
        return 0

    uid = os.environ.get("FBM_ANDROID_ID", "")
    if not uid.strip():
        parser.error("Falta FBM_ANDROID_ID; no se genera ni se supone un UID")
    fields = registration_fields(
        uid=uid.strip(), plataforma="Android " + args.android_release.strip(),
        tipo_dispositivo="mobile", version="5.0.42"
    )
    try:
        response = post_device_form(fields)
        extract_identity_fields(response)
    except (RuntimeError, ValueError) as exc:
        # No imprimimos la respuesta, el UID ni claves de sesión.
        print("Registro no validado: " + type(exc).__name__, file=sys.stderr)
        return 1
    print("Registro aceptado: se recibieron key e idDispositivo (valores ocultos).")
    print("Aviso: la sesión no se guarda; esto no valida todavía la búsqueda.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
