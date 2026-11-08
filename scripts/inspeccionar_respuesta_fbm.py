#!/usr/bin/env python3
"""Inspección segura de respuestas de la fuente Afición FBM.

No realiza llamadas de red. Analiza una respuesta JSON que el usuario haya
obtenido legítimamente y evita mostrar valores potencialmente sensibles.
Uso: python3 scripts/inspeccionar_respuesta_fbm.py respuesta.json
"""
import json
import sys
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
SENSITIVE = ("token", "key", "clave", "secret", "cookie", "password", "authorization",
             "device", "dispositivo", "email", "telefono", "phone", "session",
             "sesion", "dni", "nombre", "apellido", "direccion", "address")


def describe(value, *, depth=0):
    """Resumir únicamente estructura y tipos, nunca valores privados."""
    if depth >= 5:
        return {"tipo": type(value).__name__, "profundidad_limite": True}
    if isinstance(value, dict):
        safe = {}
        for key, child in list(value.items())[:100]:
            label = str(key)
            if any(secret in label.lower() for secret in SENSITIVE):
                # Tampoco publicar el nombre exacto del campo sensible.
                safe["<campo_sensible>"] = "<omitido>"
            else:
                safe[label] = describe(child, depth=depth + 1)
        return {"tipo": "objeto", "campos": safe, "truncado": len(value) > 100}
    if isinstance(value, list):
        return {"tipo": "lista", "longitud": len(value),
                "primer_elemento": describe(value[0], depth=depth + 1) if value else None}
    return {"tipo": type(value).__name__}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Uso: python3 scripts/inspeccionar_respuesta_fbm.py respuesta.json", file=sys.stderr)
        return 2
    path = Path(args[0])
    if path.stat().st_size > MAX_BYTES:
        print("Archivo demasiado grande", file=sys.stderr)
        return 2
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    print(json.dumps(describe(data), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
