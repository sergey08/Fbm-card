#!/usr/bin/env python3
"""Verifica evidencia localizada en el APK 5.0.42, sin red ni secretos."""
import argparse
import hashlib
import io
import struct
import zipfile

EXPECTED = "705267ff6111bbf98a4e87fb83db96ba90178164ae7d7fa347c205191b8c6ff1"


def verify(data):
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise ValueError("classes2.dex no coincide con la version examinada")
    u16 = lambda p: struct.unpack_from("<H", data, p)[0]
    u32 = lambda p: struct.unpack_from("<I", data, p)[0]
    strings_offset = u32(60)

    def string(index):
        p = u32(strings_offset + index * 4)
        while data[p] & 128:
            p += 1
        p += 1
        return data[p:data.index(b"\0", p)].decode("utf-8")

    def literal(offset, expected):
        if data[offset] != 0x1a or string(u16(offset + 2)) != expected:
            raise ValueError("Literal inesperado")

    literal(5684274, "https://appaficionfbm.gesdeportiva.es/v2/equipo.ashx")
    if data[5684278] != 0x5b or u16(5684280) != 0x67c0:
        raise ValueError("Asignacion de URL inesperada")
    for field_offset, url_offset in ((5678882, 5678914), (5679646, 5679678),
                                     (5680482, 5680514), (5681318, 5681350)):
        if data[field_offset] != 0x54 or u16(field_offset + 2) != 0x67c0:
            raise ValueError("Lectura de URL inesperada")
        if data[url_offset] != 0x71 or u16(url_offset + 2) != 0x7a77:
            raise ValueError("Invocacion de URL inesperada")
    for offset, text in ((5678948, "accion"), (5678952, "fasesGrupos"),
                         (5678962, "id_dispositivo"), (5678986, "key"),
                         (5679078, "id_equipo"), (5679716, "horariosFecha"),
                         (5680552, "horariosJornadas"), (5681388, "detalleEquipo")):
        literal(offset, text)
    literal(1376762, "")  # id_ronda vacio en una ruta de LA5/g0;->g
    literal(2407364, "00:00")
    literal(2407370, "23:59")
    literal(2407390, "-")
    literal(2407418, " ")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", help="ZIP de split APKs proporcionado por el usuario")
    args = parser.parse_args()
    try:
        with zipfile.ZipFile(args.archivo) as splits:
            with zipfile.ZipFile(io.BytesIO(splits.read("base.apk"))) as apk:
                verify(apk.read("classes2.dex"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        parser.exit(1, "No se pudo verificar el APK indicado.\n")
    print("Evidencia verificada: equipo.ashx, fasesGrupos, horariosFecha, horariosJornadas y detalleEquipo.")


if __name__ == "__main__":
    main()
