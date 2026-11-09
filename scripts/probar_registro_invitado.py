#!/usr/bin/env python3
"""Diagnostico experimental de registro: sin red salvo con --enviar."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

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


def error_marker(response):
    """Identifica solo literales comunes, sin atribuirles significado."""
    if "error" not in response:
        return "ausente"
    value = response["error"]
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "booleano_true" if value else "booleano_false"
    if type(value) in (int, float) and value in (0, 1):
        return "numero_0" if value == 0 else "numero_1"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("", "0", "1", "true", "false", "ok", "success", "null"):
            return "texto_" + (normalized or "vacio")
    return "otro_valor_oculto"


def save_error(path, response):
    """Guarda solo el campo error en un archivo nuevo para revision local."""
    if "error" not in response:
        raise ValueError("Campo error ausente")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump({"error": response["error"]}, output, ensure_ascii=False)
        output.write("\n")


def save_candidate(path, uid, response):
    """Conserva solo el identificador candidato y su vinculo con el UID local."""
    device_id = response.get("id_dispositivo")
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("Sin identificador candidato")
    data = {"format": 1, "uid_sha256": hashlib.sha256(uid.encode()).hexdigest(),
            "id_dispositivo": device_id}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(data, output)
        output.write("\n")


def load_candidate(path, uid):
    with open(path, encoding="utf-8") as source:
        data = json.load(source)
    if (not isinstance(data, dict) or set(data) != {"format", "uid_sha256", "id_dispositivo"}
            or type(data["format"]) is not int or data["format"] != 1
            or data["uid_sha256"] != hashlib.sha256(uid.encode()).hexdigest()
            or not isinstance(data["id_dispositivo"], str) or not data["id_dispositivo"].strip()):
        raise ValueError("Identificador candidato invalido o de otra identidad")
    return data["id_dispositivo"]


def search_once(device_id, key, text):
    """Una busqueda experimental; no registra ni muestra datos privados."""
    fields = {"accion": "buscarEquipo", "id_dispositivo": device_id,
              "key": key, "texto": text, "skip": "0"}
    request = urllib.request.Request(
        "https://appaficionfbm.gesdeportiva.es/v2/busqueda.ashx",
        data=urllib.parse.urlencode(fields).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "FBMCard-DEV/0.1"})
    try:
        with protocol.open_request(request, timeout=12) as response:
            if response.status != 200:
                raise RuntimeError("http")
            raw = response.read(131073)
    except (urllib.error.URLError, OSError, TimeoutError):
        raise RuntimeError("transporte") from None
    if len(raw) > 131072:
        raise RuntimeError("respuesta_grande")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise RuntimeError("json_invalido") from None
    if not isinstance(result, dict):
        raise RuntimeError("json_no_objeto")
    return result


def phases_once(device_id, key, team_id):
    """Una consulta experimental fasesGrupos, basada en APK 5.0.42."""
    fields = {"accion": "fasesGrupos", "id_dispositivo": device_id,
              "key": key, "id_equipo": team_id}
    request = urllib.request.Request(
        "https://appaficionfbm.gesdeportiva.es/v2/equipo.ashx",
        data=urllib.parse.urlencode(fields).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "FBMCard-DEV/0.1"})
    try:
        with protocol.open_request(request, timeout=12) as response:
            if response.status != 200:
                raise RuntimeError("http")
            raw = response.read(131073)
    except (urllib.error.URLError, OSError, TimeoutError):
        raise RuntimeError("transporte") from None
    if len(raw) > 131072:
        raise RuntimeError("respuesta_grande")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise RuntimeError("json_invalido") from None
    if not isinstance(result, dict):
        raise RuntimeError("json_no_objeto")
    return result


def schedule_fields(device_id, key, team_id, phases, start, end):
    """Contrato experimental observado: seleccion actual sin rondas."""
    if not isinstance(phases, dict) or phases.get("error") != "":
        raise ValueError("Respuesta de fases ambigua")
    pid, gid = phases.get("faseActual"), phases.get("grupoActual")
    all_phases = phases.get("listaFasesGrupo")
    if not all(isinstance(v, str) and v.strip() for v in (device_id, key, team_id, pid, gid)) or not isinstance(all_phases, list):
        raise ValueError("Identificadores incompletos")
    matched = [p for p in all_phases if isinstance(p, dict) and p.get("IdFase") == pid]
    if len(matched) != 1:
        raise ValueError("Fase ambigua")
    phase = matched[0]
    groups, rounds = phase.get("Grupos"), phase.get("Rondas")
    if not isinstance(groups, list) or sum(isinstance(g, dict) and g.get("IdGrupo") == gid for g in groups) != 1:
        raise ValueError("Grupo ambiguo")
    if not isinstance(rounds, list) or rounds:
        raise ValueError("La seleccion de rondas aun no esta implementada")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or (last - first).days > 366:
        raise ValueError("Rango de fechas invalido")
    return {"accion": "horariosJornadas", "id_dispositivo": device_id, "key": key,
            "id_equipo": team_id, "id_fase": pid, "id_grupo": gid, "id_ronda": "",
            "fecha_inicial": first.isoformat() + " 00:00",
            "fecha_final": last.isoformat() + " 23:59"}


def schedule_once(fields):
    request = urllib.request.Request(
        "https://appaficionfbm.gesdeportiva.es/v2/equipo.ashx",
        data=urllib.parse.urlencode(fields).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "FBMCard-DEV/0.1"})
    try:
        with protocol.open_request(request, timeout=12) as response:
            if response.status != 200:
                raise RuntimeError("http")
            raw = response.read(131073)
    except (urllib.error.URLError, OSError, TimeoutError):
        raise RuntimeError("transporte") from None
    if len(raw) > 131072:
        raise RuntimeError("respuesta_grande")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise RuntimeError("json_invalido") from None
    if not isinstance(result, dict):
        raise RuntimeError("json_no_objeto")
    return result


def classification_fields(device_id, key, phases):
    """Clasificacion de grupo actual; no deduce grupos ni tipo de fase."""
    if not isinstance(phases, dict) or phases.get("error") != "":
        raise ValueError("Respuesta de fases ambigua")
    phase_id, group_id, items = phases.get("faseActual"), phases.get("grupoActual"), phases.get("listaFasesGrupo")
    if not all(isinstance(x, str) and x.strip() for x in (device_id, key, phase_id, group_id)) or not isinstance(items, list):
        raise ValueError("Faltan datos para clasificacion")
    phases_found = [p for p in items if isinstance(p, dict) and p.get("IdFase") == phase_id]
    if len(phases_found) != 1:
        raise ValueError("Fase ambigua")
    phase = phases_found[0]
    groups, phase_type = phase.get("Grupos"), phase.get("TipoFase")
    if not isinstance(groups, list) or sum(isinstance(g, dict) and g.get("IdGrupo") == group_id for g in groups) != 1:
        raise ValueError("Grupo ambiguo")
    if not isinstance(phase_type, str) or not phase_type.strip():
        raise ValueError("Tipo de fase no disponible")
    return {"accion": "clasificacion", "id_dispositivo": device_id, "key": key,
            "id_grupo": group_id, "tipo_fase": phase_type}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-release", required=True,
                        help="Version Android declarada para el experimento, por ejemplo 16")
    parser.add_argument("--identidad", type=Path,
                        help="Ruta privada del archivo de identidad local")
    parser.add_argument("--guardar-error", type=Path,
                        help="Guarda el campo error en un archivo nuevo para revision privada")
    parser.add_argument("--candidato", type=Path,
                        help="Archivo privado nuevo al registrar, existente al probar acceso")
    parser.add_argument("--guardar-equipos", type=Path,
                        help="Guarda solo la lista de equipos para revision local")
    parser.add_argument("--equipo", type=Path, help="Archivo de equipo seleccionado localmente")
    parser.add_argument("--guardar-fases", type=Path,
                        help="Guarda la respuesta de fases para revision privada")
    parser.add_argument("--desde", help="Primera fecha ISO AAAA-MM-DD")
    parser.add_argument("--hasta", help="Ultima fecha ISO AAAA-MM-DD")
    parser.add_argument("--guardar-horarios", type=Path, help="Archivo nuevo para revision privada")
    parser.add_argument("--guardar-clasificacion", type=Path, help="Archivo nuevo para revision privada")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--crear-identidad", action="store_true",
                        help="Crea una identidad local, sin red y sin sobrescribir")
    action.add_argument("--enviar", action="store_true",
                        help="Autoriza un unico POST de registro experimental")
    action.add_argument("--acceder", action="store_true",
                        help="Autoriza un POST de acceso experimental con el candidato guardado")
    action.add_argument("--buscar-equipo", metavar="TEXTO",
                        help="Autoriza acceso y una busqueda experimental de equipo")
    action.add_argument("--fases", action="store_true",
                        help="Autoriza acceso y una consulta experimental de fases del equipo")
    action.add_argument("--horarios", action="store_true",
                        help="Autoriza acceso, fases y una consulta experimental de horarios")
    action.add_argument("--clasificacion", action="store_true",
                        help="Autoriza acceso, fases y una consulta experimental de clasificacion")
    args = parser.parse_args(argv)
    if args.clasificacion and (not args.equipo or not args.candidato):
        parser.error("--clasificacion requiere --equipo y --candidato")
    if args.guardar_clasificacion and not args.clasificacion:
        parser.error("--guardar-clasificacion requiere --clasificacion")
    if args.horarios and (not args.equipo or not args.candidato or not args.desde or not args.hasta):
        parser.error("--horarios requiere --equipo, --candidato, --desde y --hasta")
    if (args.desde or args.hasta or args.guardar_horarios) and not args.horarios:
        parser.error("Fechas y --guardar-horarios requieren --horarios")
    if args.horarios:
        try:
            first, last = date.fromisoformat(args.desde), date.fromisoformat(args.hasta)
            if first > last or (last - first).days > 366:
                raise ValueError
        except ValueError:
            parser.error("Fechas invalidas o rango superior a 366 dias")
    if args.guardar_fases and not args.fases:
        parser.error("--guardar-fases requiere --fases")
    if args.guardar_equipos and args.buscar_equipo is None:
        parser.error("--guardar-equipos requiere --buscar-equipo")
    if args.guardar_error and not (args.enviar or args.acceder):
        parser.error("--guardar-error requiere --enviar o --acceder")
    if args.candidato and not (args.enviar or args.acceder or args.buscar_equipo is not None or args.fases or args.horarios or args.clasificacion):
        parser.error("--candidato requiere --enviar o --acceder")
    if (args.acceder or args.buscar_equipo is not None or args.fases) and not args.candidato:
        parser.error("El acceso o busqueda requiere --candidato")
    if args.buscar_equipo is not None and not args.buscar_equipo.strip():
        parser.error("El texto de busqueda no puede estar vacio")
    if not args.android_release.strip():
        parser.error("La version de Android no puede estar vacia")
    if args.fases and not args.equipo:
        parser.error("--fases requiere --equipo")
    if args.equipo and not (args.fases or args.horarios or args.clasificacion):
        parser.error("--equipo requiere --fases, --horarios o --clasificacion")
    if not args.crear_identidad and not args.enviar and not args.acceder and args.buscar_equipo is None and not args.fases and not args.horarios and not args.clasificacion:
        print("SIN RED: formulario previsto: accion=registrar, uid=<privado>, "
              "plataforma=Android <version>, tipo_dispositivo=mobile, version=5.0.42")
        print("Crea una identidad propia con --identidad RUTA --crear-identidad; "
              "para enviar usa --identidad RUTA --enviar.")
        return 0
    if not args.identidad:
        parser.error("Se requiere --identidad RUTA")
    if args.guardar_error and os.path.lexists(args.guardar_error):
        print("El archivo de error ya existe; no se envio ninguna peticion.", file=sys.stderr)
        return 1
    if args.guardar_equipos and os.path.lexists(args.guardar_equipos):
        print("El archivo de equipos ya existe; no se envio ninguna peticion.", file=sys.stderr)
        return 1
    if args.guardar_fases and os.path.lexists(args.guardar_fases):
        print("El archivo de fases ya existe; no se envio ninguna peticion.", file=sys.stderr)
        return 1
    if args.guardar_horarios and os.path.lexists(args.guardar_horarios):
        print("El archivo de horarios ya existe; no se envio ninguna peticion.", file=sys.stderr)
        return 1
    if args.guardar_clasificacion and os.path.lexists(args.guardar_clasificacion):
        print("El archivo de clasificacion ya existe; no se envio ninguna peticion.", file=sys.stderr)
        return 1
    if args.enviar and args.candidato and os.path.lexists(args.candidato):
        print("El archivo de candidato ya existe; no se envio ninguna peticion.", file=sys.stderr)
        return 1
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
    if args.fases or args.horarios or args.clasificacion:
        try:
            with open(args.equipo, encoding="utf-8") as source:
                team = json.load(source)
            team_id = team.get("Id") if isinstance(team, dict) else None
            if not isinstance(team_id, str) or not team_id.strip():
                raise ValueError("Id ausente")
        except (OSError, ValueError):
            print("Equipo seleccionado inaccesible o invalido; no se envio ninguna peticion.", file=sys.stderr)
            return 1
    try:
        if args.acceder or args.buscar_equipo is not None or args.fases or args.horarios or args.clasificacion:
            try:
                device_id = load_candidate(args.candidato, uid)
            except (OSError, ValueError):
                print("Candidato inaccesible, invalido o de otra identidad; no se envio ninguna peticion.", file=sys.stderr)
                return 1
            fields = protocol.access_fields(uid=uid, token_push="", id_dispositivo=device_id,
                plataforma="Android " + args.android_release.strip(), tipo_dispositivo="mobile", version="5.0.42")
        else:
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
    if args.guardar_error:
        try:
            save_error(args.guardar_error, response)
        except (OSError, ValueError):
            print("No se pudo guardar el campo error; no se sobrescribio ningun archivo.", file=sys.stderr)
        else:
            print("Campo error guardado localmente; revisalo antes de compartirlo.")
    if args.enviar and args.candidato:
        try:
            save_candidate(args.candidato, uid, response)
        except (OSError, ValueError):
            print("No se pudo guardar el candidato; no se sobrescribio ningun archivo.", file=sys.stderr)
        else:
            print("Identificador candidato guardado localmente; aun no esta validado.")
    if args.buscar_equipo is not None or args.fases or args.horarios or args.clasificacion:
        key = response.get("key")
        if response.get("error") != "" or not isinstance(key, str) or not key.strip():
            print("Busqueda cancelada: respuesta de acceso ambigua; valores ocultos.", file=sys.stderr)
            return 1
        returned_id = response.get("id_dispositivo")
        if returned_id not in (None, "", device_id):
            print("Busqueda cancelada: identificador de acceso distinto o invalido.", file=sys.stderr)
            return 1
        try:
            result = phases_once(device_id, key, team_id) if (args.fases or args.horarios or args.clasificacion) else search_once(device_id, key, args.buscar_equipo.strip())
        except RuntimeError as exc:
            print("Busqueda no validada: " + str(exc) + "; detalles ocultos.", file=sys.stderr)
            return 1
        if args.clasificacion:
            try:
                form = classification_fields(device_id, key, result)
                result = schedule_once(form)
            except (ValueError, RuntimeError):
                print("Clasificacion no validada: fase o grupo ambiguos, o fallo de consulta.", file=sys.stderr)
                return 1
            if args.guardar_clasificacion:
                try:
                    fd = os.open(args.guardar_clasificacion, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "w", encoding="utf-8") as output:
                        json.dump(result, output, ensure_ascii=False, indent=2)
                        output.write("\n")
                except OSError:
                    print("No se pudo guardar la respuesta de clasificacion.", file=sys.stderr)
                else:
                    print("Clasificacion guardada localmente; revisala antes de compartirla.")
            rows = result.get("clasificacion")
            count = str(len(rows)) if isinstance(rows, list) else "no_disponible"
            print("Respuesta de clasificacion: error=" + field_shape(result, "error") +
                  "; clasificacion=" + field_shape(result, "clasificacion") + "; elementos=" + count +
                  "; marcador_error=" + error_marker(result) + ". Valores ocultos; resultado no validado.")
            return 1
        if args.horarios:
            try:
                form = schedule_fields(device_id, key, team_id, result, args.desde, args.hasta)
                result = schedule_once(form)
            except (ValueError, RuntimeError):
                print("Horarios no validados: fases ambiguas, rondas presentes o fallo de consulta.", file=sys.stderr)
                return 1
            if args.guardar_horarios:
                try:
                    fd = os.open(args.guardar_horarios, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "w", encoding="utf-8") as output:
                        json.dump(result, output, ensure_ascii=False, indent=2)
                        output.write("\n")
                except OSError:
                    print("No se pudo guardar la respuesta de horarios.", file=sys.stderr)
                else:
                    print("Respuesta de horarios guardada localmente; revisala antes de compartirla.")
            print("Respuesta de horarios recibida; error=" + field_shape(result, "error") +
                  "; marcador_error=" + error_marker(result) + ". Valores ocultos; resultado no validado.")
            return 1
        if args.fases:
            if args.guardar_fases:
                try:
                    fd = os.open(args.guardar_fases, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "w", encoding="utf-8") as output:
                        json.dump(result, output, ensure_ascii=False, indent=2)
                        output.write("\n")
                except OSError:
                    print("No se pudo guardar la respuesta; no se sobrescribio ningun archivo.", file=sys.stderr)
                else:
                    print("Respuesta de fases guardada localmente; revisala antes de compartirla.")
            print("Respuesta de fases recibida; " +
                  ", ".join(f"{name}={field_shape(result, name)}" for name in ("error", "resultado", "fases", "grupos")) +
                  "; marcador_error=" + error_marker(result) + ". Valores ocultos; resultado no validado.")
            return 1
        names = ("error", "resultado", "equipos", "datos")
        shapes = ", ".join(f"{name}={field_shape(result, name)}" for name in names)
        equipos = result.get("equipos")
        count = str(len(equipos)) if isinstance(equipos, list) else "no_disponible"
        if args.guardar_equipos:
            if not isinstance(equipos, list):
                print("No se pudo guardar: equipos no es una lista.", file=sys.stderr)
            else:
                try:
                    fd = os.open(args.guardar_equipos, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "w", encoding="utf-8") as output:
                        json.dump(equipos, output, ensure_ascii=False, indent=2)
                        output.write("\n")
                except OSError:
                    print("No se pudo guardar la lista; no se sobrescribio ningun archivo.", file=sys.stderr)
                else:
                    print("Lista de equipos guardada localmente; revisala antes de compartirla.")
        print("Respuesta de busqueda recibida; campos conocidos: " + shapes +
              "; numero_equipos=" + count + "; marcador_error=" + error_marker(result) +
              ". No se muestran valores; resultado no validado.")
        return 1
    if args.acceder:
        names = ("key", "idDispositivo", "dispositivoId", "id_dispositivo", "error")
        shapes = ", ".join(f"{name}={field_shape(response, name)}" for name in names)
        print("Acceso no validado: " + shapes + "; marcador_error=" + error_marker(response) +
              ". Valores ocultos; significado no verificado.")
        return 1
    try:
        extract_identity_fields(response)
    except ValueError:
        # Solo presencia y tipo de los campos previstos, nunca valores o claves arbitrarias.
        names = ("key", "idDispositivo", "dispositivoId", "id_dispositivo", "error")
        shapes = ", ".join(f"{name}={field_shape(response, name)}" for name in names)
        print("Registro no validado: estructura de campos conocidos: " + shapes +
              "; marcador_error=" + error_marker(response) +
              ". Valores ocultos; el significado del marcador no esta verificado.", file=sys.stderr)
        return 1
    print("Respuesta de registro con campos validados localmente (valores ocultos).")
    print("La sesion no se guarda; esto no valida la busqueda ni el acceso posterior.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
