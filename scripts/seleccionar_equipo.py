#!/usr/bin/env python3
"""Seleccion local de resultados de busqueda FBM, sin conexion de red."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

FIELDS = ("Id", "Nombre", "Club", "Categoria", "Temporada")


def read_teams(path):
    with open(path, encoding="utf-8-sig") as source:
        teams = json.load(source)
    if not isinstance(teams, list):
        raise ValueError("El archivo no contiene una lista")
    for team in teams:
        if not isinstance(team, dict) or any(
            not isinstance(team.get(k), str) or not team[k].strip() for k in FIELDS
        ):
            raise ValueError("Hay un equipo sin datos necesarios para seleccionarlo")
    return teams


def save_selection(path, team):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump({k: team[k] for k in FIELDS}, output, ensure_ascii=False, indent=2)
        output.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equipos", type=Path, required=True, help="Lista JSON de la busqueda")
    parser.add_argument("--numero", type=int, help="Numero de equipo que aparece en la lista")
    parser.add_argument("--salida", type=Path, help="Archivo nuevo para guardar la seleccion")
    args = parser.parse_args(argv)
    if (args.numero is None) != (args.salida is None):
        parser.error("--numero y --salida deben usarse juntos")
    try:
        teams = read_teams(args.equipos)
    except (OSError, ValueError):
        print("No se puede leer una lista de equipos valida.", file=sys.stderr)
        return 1
    if args.numero is None:
        if not teams:
            print("No hay equipos en la lista.")
        for index, team in enumerate(teams, 1):
            print(f"{index}. {team['Nombre']} | {team['Club']} | {team['Categoria']} | {team['Temporada']}")
        return 0
    if not 1 <= args.numero <= len(teams):
        print("Numero de equipo fuera de la lista; no se ha guardado nada.", file=sys.stderr)
        return 1
    try:
        save_selection(args.salida, teams[args.numero - 1])
    except OSError:
        print("No se ha podido guardar la seleccion; no se sobrescriben archivos.", file=sys.stderr)
        return 1
    print("Equipo guardado localmente; se ha conservado su Id original.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
