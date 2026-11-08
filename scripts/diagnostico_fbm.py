#!/usr/bin/env python3
"""Diagnóstico mínimo de acceso invitado a Afición FBM.

Solo envía una consulta de prueba con los cinco campos observados en el APK,
con identidad vacía: NO constituye una prueba de sesión invitada válida.
No imprime valores de la respuesta ni datos de jugadores/equipos.
"""
import json
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://appaficionfbm.gesdeportiva.es/v2/busqueda.ashx"
HOST = "appaficionfbm.gesdeportiva.es"
TIMEOUT = 12


def diagnose_dns():
    try:
        socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM)
        return True
    except OSError:
        print("DNS: no se puede resolver el servidor Afición FBM desde este equipo.")
        print("Esto no permite concluir si la API acepta consultas de invitados.")
        return False


def main():
    if not diagnose_dns():
        return 2
    request = urllib.request.Request(
        BASE,
        data=urllib.parse.urlencode(
            {"accion": "buscarEquipo", "id_dispositivo": "", "key": "", "texto": "PINTOBASKET", "skip": "0"}
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "FBMCard-DEV/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(32769)
            print("HTTP:", response.status)
            if len(raw) > 32768:
                print("Respuesta demasiado grande para el diagnóstico.")
                return 2
            try:
                parsed = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                print("El servidor no devolvió un JSON válido.")
                return 2
            if not isinstance(parsed, dict):
                print("Estructura JSON no esperada.")
                return 2
            print("Claves de nivel superior:", ", ".join(sorted(
                str(key) for key in parsed if str(key).lower() not in
                {"key", "token", "id_dispositivo", "password", "cookie"}
            )))
            if parsed.get("resultado") == "error":
                print("El servidor responde, pero esta solicitud no ha funcionado.")
                print("Puede faltar el protocolo de sesión invitada u otros parámetros.")
                return 1
            print("Respuesta recibida; falta verificar que incluya equipos reales y acceso permitido.")
            return 0
    except urllib.error.HTTPError as error:
        print("HTTP:", error.code, "- solicitud rechazada.")
        return 1
    except (urllib.error.URLError, TimeoutError, OSError):
        print("No se ha podido completar la conexión HTTPS.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
