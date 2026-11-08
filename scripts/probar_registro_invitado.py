#!/usr/bin/env python3
"""Diagnostico experimental de registro: sin red salvo con --enviar."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys

ROOT = Path(__file__).resolve().parent
if not (ROOT / "custom_components" / "fbm" / "device_protocol.py").is_file():
    ROOT = ROOT.parent
spec = importlib.util.spec_from_file_location(
    "fbm_device_protocol_diagnostic", ROOT / "custom_components/fbm/device_protocol.py")
protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protocol)
registration_fields = protocol.registration_fields
post_device_form = protocol.post_device_form
extract_identity_fields = protocol.extract_identity_fields


def create_identity(path):
    """Crear una identidad propia; nunca reemplazar una existente."""
    uid = secrets.token_hex(8)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump({"format": 1, "uid": uid}, output)
        output.write("\n")


def load_identity(path):
    with open(path, encoding="utf-8") as source:
        data = json.load(source)
    if (not isinstance(data, dict) or set(data) != {"format", "uid"}
            or type(data["format"]) is not int or data["format"] != 1
            or not isinstance(data["uid"], str)
            or not re.fullmatch(r"[0-9a-f]{16}", data["uid"])):
        raise ValueError("Formato de identidad no valido")
    return data["uid"]


def field_shape(response, name):
    """Solo clasifica campos conocidos, sin exponer valores del servidor."""
    if name not in response:
        return "ausente"
    value = response[name]
    if value is None:
        return "nulo"
    if isinstance(value, bool):
        return "booleano"
    if isinstance(value, str):
        return "texto_no_vacio" if value else "texto_vacio"
    if isinstance(value, (int, float)):
        return "numero"
    if isinstance(value, dict):
        return "objeto"
    if isinstance(value, list):
        return "lista"
    return "otro"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-release", required=True,
                        help="Version Android declarada para el experimento, por ejemplo 16")
    parser.add_argument("--identidad", type=Path,
                        help="Ruta privada del archivo de identidad local")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--crear-identidad", action="store_true",
                        help="Crea una identidad local, sin red y sin sobrescribir")
    action.add_argument("--enviar", action="store_true",
                        help="Autoriza un unico POST de registro experimental")
    args = parser.parse_args(argv)
    if not args.android_release.strip():
        parser.error("La version de Android no puede estar vacia")
    if not args.crear_identidad and not args.enviar:
        print("SIN RED: formulario previsto: accion=registrar, uid=<privado>, "
              "plataforma=Android <version>, tipo_dispositivo=mobile, version=5.0.42")
        print("Crea una identidad propia con --identidad RUTA --crear-identidad; "
              "para enviar usa --identidad RUTA --enviar.")
        return 0
    if not args.identidad:
        parser.error("Se requiere --identidad RUTA")
    if args.crear_identidad:
        try:
            create_identity(args.identidad)
        except OSError:
            print("No se pudo crear la identidad; comprueba la ruta y que no exista.", file=sys.stderr)
            return 1
        print("Identidad propia creada localmente. No se ha enviado ninguna peticion.")
        return 0
    try:
        uid = load_identity(args.identidad)
    except (OSError, ValueError):
        print("Identidad local inaccesible o invalida; no se envio ninguna peticion.", file=sys.stderr)
        return 1
    try:
        fields = registration_fields(uid=uid, plataforma="Android " + args.android_release.strip(),
                                     tipo_dispositivo="mobile", version="5.0.42")
        response = post_device_form(fields)
    except protocol.DeviceTransportError as exc:
        if exc.category == "http":
            print(f"Registro no validado: HTTP {exc.status}; cuerpo oculto.", file=sys.stderr)
        else:
            print(f"Registro no validado: {exc.category}; detalles ocultos.", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError):
        print("Registro no validado: fallo de transporte o formulario; detalles ocultos.", file=sys.stderr)
        return 1
    try:
        extract_identity_fields(response)
    except ValueError:
        # Solo presencia y tipo de los campos previstos, nunca valores o claves arbitrarias.
        names = ("key", "idDispositivo", "dispositivoId", "id_dispositivo", "error")
        shapes = ", ".join(f"{name}={field_shape(response, name)}" for name in names)
        print("Registro no validado: estructura de campos conocidos: " + shapes +
              ". Valores ocultos; no se interpreta el campo error.", file=sys.stderr)
        return 1
    print("Respuesta con key e idDispositivo recibida (valores ocultos).")
    print("La sesion no se guarda; esto no valida la busqueda ni el acceso posterior.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
