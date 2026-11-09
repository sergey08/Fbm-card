#!/usr/bin/env python3
"""Muestra los partidos guardados localmente sin exponer datos de sesion."""
import argparse
import json
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="Respuesta local guardada por el diagnostico")
    args = parser.parse_args(argv)
    try:
        with args.archivo.open(encoding="utf-8-sig") as source:
            data = json.load(source)
        if not isinstance(data, dict) or data.get("error") != "" or not isinstance(data.get("partidos"), list):
            raise ValueError("Respuesta no valida")
        partidos = data["partidos"]
        for partido in partidos:
            if not isinstance(partido, dict) or any(not isinstance(partido.get(k), str) or not partido[k].strip()
                for k in ("NombreEquipoLocal", "NombreEquipoVisitante")):
                raise ValueError("Partido sin equipos")
    except (OSError, ValueError):
        print("No se puede leer una respuesta valida de horarios.", file=sys.stderr)
        return 1
    print(f"Partidos: {len(partidos)} | Jornada actual: {data.get('jornadaActual', 'no disponible')}")
    for partido in partidos:
        fecha = partido.get("Fecha") or "sin fecha"
        hora = partido.get("Hora") or "sin hora"
        jornada = partido.get("NumeroJornada")
        print(f"Jornada {jornada if type(jornada) is int else '?'} | {fecha} {hora} | "
              f"{partido['NombreEquipoLocal']} - {partido['NombreEquipoVisitante']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
