#!/usr/bin/env python3
"""Muestra los partidos guardados localmente sin exponer datos de sesion."""
import argparse
import json
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="Respuesta local guardada por el diagnostico")
    parser.add_argument("--equipo", type=Path, help="Filtra por el nombre exacto del equipo seleccionado")
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
        selected = None
        if args.equipo:
            with args.equipo.open(encoding="utf-8-sig") as source:
                team = json.load(source)
            selected = team.get("Nombre") if isinstance(team, dict) else None
            if not isinstance(selected, str) or not selected.strip():
                raise ValueError("Equipo sin nombre")
    except (OSError, ValueError):
        print("No se puede leer una respuesta valida de horarios.", file=sys.stderr)
        return 1
    total = len(partidos)
    if selected is not None:
        target = selected.strip().casefold()
        partidos = [p for p in partidos if any(p[k].strip().casefold() == target
                    for k in ("NombreEquipoLocal", "NombreEquipoVisitante"))]
        print(f"Partidos con el nombre seleccionado: {len(partidos)} de {total}. La coincidencia es por nombre.")
    else:
        print(f"Partidos devueltos por FBM: {total} (pueden incluir todo el grupo).")
    print(f"Jornada actual: {data.get('jornadaActual', 'no disponible')}")
    for partido in partidos:
        fecha = partido.get("Fecha") or "sin fecha"
        hora = partido.get("Hora") or "sin hora"
        jornada = partido.get("NumeroJornada")
        print(f"Jornada {jornada if type(jornada) is int else '?'} | {fecha} {hora} | "
              f"{partido['NombreEquipoLocal']} - {partido['NombreEquipoVisitante']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
