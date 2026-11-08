#!/usr/bin/env python3
"""Diagnóstico de conectividad con la API OFICIAL Afición FBM.

No extrae resultados de terceros, no inventa credenciales y no evade controles.
Uso: python3 scripts/diagnostico_fbm.py
"""
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://appaficionfbm.gesdeportiva.es/v2/busqueda.ashx"
TIMEOUT = 12

def main():
    request = urllib.request.Request(
        BASE,
        data=urllib.parse.urlencode({"accion": "buscarEquipo", "texto": "PINTOBASKET", "skip": "0"}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "FBMCard-DEV/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = response.read(32768).decode("utf-8", errors="replace")
            print("HTTP:", response.status)
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                print("Respuesta no JSON (primeros 500 caracteres):", payload[:500])
                return 2
            if isinstance(parsed, dict):
                print("Resultado:", parsed.get("resultado", "(sin resultado)"))
                print("Error:", parsed.get("error", "(sin error)"))
                print("Campos:", ", ".join(sorted(parsed)))
                if parsed.get("resultado") == "error":
                    print("API alcanzable; no se ha validado una búsqueda de equipos sin credenciales.")
                    return 1
                print("Revisar manualmente que los datos sean oficiales y correspondan a la acción solicitada.")
                return 0
            print("Respuesta JSON inesperada:", type(parsed).__name__)
            return 2
    except urllib.error.HTTPError as error:
        print("HTTP:", error.code, "- servidor rechazó la petición")
        return 1
    except (urllib.error.URLError, TimeoutError) as error:
        print("Conectividad no confirmada:", str(error))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
