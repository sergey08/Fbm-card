"""Read-only FBM diagnostics: strict allowlisted schema metadata, no values.

Never surface raw responses, auth fields, request bodies, IDs or exception strings.
"""
from __future__ import annotations
import re

SCHEDULE_KEYS = frozenset({
    "error", "partidos", "jornadas", "jornadaActual", "resultado", "listaJornadas",
})
ROSTER_KEYS = frozenset({
    "error", "misJugadores", "misjugadores", "jugadores", "total", "equipo",
})
ROSTER_ROW_KEYS = frozenset({
    "id", "nombre", "nombreEquipo", "temporada", "partidosJugados",
    "puntosTotales", "mediaPuntos", "puntosPorPartido", "minutosPorPartido",
})


def safe_error_category(exc: Exception) -> str:
    """Type-only diagnosis: never serialize exception messages or URLs."""
    code = getattr(exc, "code", None)
    if code in {"http_non_200", "network", "response_too_large", "invalid_json", "non_object_json"}:
        return code
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, (ConnectionError, OSError)):
        return "transport"
    if isinstance(exc, ValueError):
        return "invalid_payload_or_parameters"
    if isinstance(exc, RuntimeError):
        return "request_failed"
    return "unexpected"


def safe_payload_shape(payload: object, *, kind: str) -> dict:
    """Summary of known field presence/types, not arbitrary response keys."""
    keys = SCHEDULE_KEYS if kind == "schedule" else ROSTER_KEYS
    if type(payload) is not dict:
        return {"type": type(payload).__name__ if type(payload) in (list, str, int, bool, type(None)) else "other"}
    # Field names only; accept identifier-like ASCII keys, never arbitrary values.
    safe_keys = sorted(k for k in payload if isinstance(k, str)
                       and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", k)
                       and k.lower() not in {"key", "authorization", "token", "id_dispositivo", "uid", "password", "secret", "cookie", "session"})[:40]
    result = {
        "top_level_keys": safe_keys,
        "type": "object",
        "present": sorted(k for k in keys if k in payload),
        "error_type": type(payload["error"]).__name__ if "error" in payload else "missing",
        "error_empty_string": payload.get("error") == "",
    }
    for name in ("partidos", "jornadas", "listaJornadas", "misJugadores", "misjugadores", "jugadores"):
        if name not in keys:
            continue
        v = payload.get(name)
        if isinstance(v, list):
            result[name + "_count"] = len(v)
            if kind == "roster" and v and type(v[0]) is dict:
                row = v[0]
                result["first_row_present"] = sorted(k for k in ROSTER_ROW_KEYS if k in row)
                # Only key names and type labels; never the player/ID values.
                keys_only = sorted(k for k in row if type(k) is str
                                   and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", k)
                                   and k.lower() not in {"key", "authorization", "token", "id_dispositivo",
                                                         "uid", "password", "secret", "cookie", "session"})[:50]
                result["first_row_keys"] = keys_only
                result["first_row_types"] = {k: ("null" if row[k] is None else
                    "string" if type(row[k]) is str else
                    "number" if type(row[k]) in (int, float) else
                    "boolean" if type(row[k]) is bool else
                    "object" if type(row[k]) is dict else
                    "array" if type(row[k]) is list else "other")
                    for k in keys_only}
                if "Foto" in row:
                    result["player_photo_reference"] = _image_reference_kind(row["Foto"])
                if "Foto" in row and type(row["Foto"]) is str:
                    value = row["Foto"]
                    result["player_photo_format"] = _image_reference_shape(value)
        elif name in payload:
            result[name + "_type"] = type(v).__name__ if type(v) in (str, dict, int, bool, type(None)) else "other"
    if kind == "schedule":
        matches = payload.get("partidos")
        if type(matches) is list and matches and type(matches[0]) is dict:
            first = matches[0]
            names = ("EscudoLocal", "EscudoVisitante", "escudoLocal",
                     "escudoVisitante", "IdEquipoLocal", "IdEquipoVisitante",
                     "idEquipoLocal", "idEquipoVisitante", "LogoLocal", "LogoVisitante",
                     "ImgEquipoLocal", "ImgEquipoVisitante", "imgEquipoLocal",
                     "imgEquipoVisitante", "escudoEquipoLocal", "escudoEquipoVisitante")
            result["match_image_fields"] = [key for key in names if key in first]
            result["match_image_types"] = {
                key: _image_reference_shape(first[key]) for key in names if key in first
            }
    return result


def _image_reference_kind(value: object) -> str:
    """Classify an image reference without returning URLs, IDs or photographs."""
    if value is None:
        return "null"
    if type(value) is not str:
        return "other"
    if not value.strip():
        return "empty"
    if value.startswith("https://"):
        return "https_url"
    if value.startswith("http://"):
        return "http_url"
    if value.startswith("data:"):
        return "inline_data"
    if value.startswith("/"):
        return "relative_path"
    if value.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image_filename"
    return "opaque_reference"


def _image_reference_shape(value: object) -> dict:
    """Only type, length band and decoded file signature; never return image IDs."""
    import base64
    import binascii
    import re
    if type(value) is not str:
        return {"kind": _image_reference_kind(value)}
    value = value.strip()
    length = len(value)
    band = ("0" if length == 0 else "1-64" if length <= 64 else
            "65-256" if length <= 256 else "257-1024" if length <= 1024 else
            "1025-16384" if length <= 16384 else "16385+")
    result = {"kind": _image_reference_kind(value), "length_band": band}
    if not value or length > 400000:
        return result
    result["text_form"] = (
        "json" if value.startswith(("{", "[")) else
        "xml" if value.startswith(("<svg", "<?xml", "<!DOCTYPE")) else
        "html" if value.startswith("<") else
        "absolute_url" if value.lower().startswith(("http://", "https://")) else
        "relative_url" if value.startswith(("/", "./", "../")) else
        "hex" if re.fullmatch(r"[0-9a-fA-F]+", value) else
        "base64" if re.fullmatch(r"[A-Za-z0-9+/_=-]+", value) else
        "other"
    )
    if result["text_form"] == "hex" and length % 2 == 0:
        try:
            decoded = bytes.fromhex(value[:min(length, 256)])
            trimmed = decoded[3:] if decoded.startswith(bytes([239,187,191])) else decoded
            result["hex_decoded_kind"] = (
                "png" if decoded.startswith(bytes([137,80,78,71,13,10,26,10])) else
                "jpeg" if decoded.startswith(bytes([255,216,255])) else
                "webp" if decoded.startswith(b"RIFF") and decoded[8:12] == b"WEBP" else
                "utf8_url" if trimmed.startswith((b"http://", b"https://")) else
                "utf16le_url" if decoded.startswith(("http".encode("utf-16le"), "HTTP".encode("utf-16le"))) else
                "json" if trimmed.startswith((b"{", b"[")) else
                "utf16le_json" if decoded.startswith(("{".encode("utf-16le"), "[".encode("utf-16le"))) else
                "utf8_text" if decoded and all((32 <= x <= 126) or x in (9,10,13) for x in decoded) else
                "utf16le_text" if len(decoded)>4 and sum(decoded[i] == 0 for i in range(1,len(decoded),2)) >= len(decoded)//4 else
                "binary_or_encoded"
            )
        except ValueError:
            result["hex_decoded_kind"] = "invalid"
    # Additional bounded, metadata-only classification for hexadecimal UTF-16LE
    # references. Never return decoded text, URLs, IDs, fragments or hashes.
    if result.get("text_form") == "hex" and result.get("hex_decoded_kind") in (
            "utf16le_text", "utf16le_url", "utf16le_json"):
        try:
            preview = bytes.fromhex(value[:min(len(value) - len(value) % 4, 4096)])
            decoded_text = preview.decode("utf-16le", errors="strict").strip("\ufeff\x00 \r\n\t")
            lowered = decoded_text.lower()
            if lowered.startswith(("https://", "http://")):
                subtype = "absolute_url"
            elif "https://" in lowered or "http://" in lowered:
                subtype = "embedded_url"
            elif lowered.startswith(("data:image/",)):
                subtype = "inline_image"
            elif lowered.startswith(("{", "[")):
                subtype = "json_like"
            elif lowered.startswith(("/", "./", "../")):
                subtype = "relative_path"
            elif re.fullmatch(r"[A-Za-z0-9+/=_-]{24,}", decoded_text):
                subtype = "base64_or_identifier"
            else:
                subtype = "opaque_text"
            result["utf16le_reference_form"] = subtype
            # Inspect the inner Base64 only for its binary signature.
            # Never expose content, sizes, or identifiers from decoded data.
            if subtype == "base64_or_identifier":
                try:
                    import base64
                    import binascii
                    if (len(decoded_text) % 4 == 0 and
                            re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", decoded_text)):
                        sample = base64.b64decode(decoded_text[:min(len(decoded_text), 128)],
                                                  validate=True)
                        result["utf16le_inner_magic"] = (
                            "png" if sample.startswith(bytes([137,80,78,71,13,10,26,10])) else
                            "jpeg" if sample.startswith(bytes([255,216,255])) else
                            "webp" if sample.startswith(b"RIFF") and sample[8:12] == b"WEBP" else
                            "other")
                    else:
                        result["utf16le_inner_magic"] = "invalid_base64"
                except (ValueError, binascii.Error):
                    result["utf16le_inner_magic"] = "invalid_base64"
            # Report presence of the official host only as a boolean.
            result["official_fbm_host_present"] = (
                "appaficionfbm.gesdeportiva.es" in lowered)
        except (ValueError, UnicodeError):
            result["utf16le_reference_form"] = "invalid"
    candidate = value
    if value.lower().startswith("data:image/") and ";base64," in value[:100]:
        candidate = value.split(";base64,", 1)[1]
    if re.fullmatch(r"[a-zA-Z0-9+/=_-]+", candidate) and len(candidate) > 12:
        try:
            sample = candidate[:64].replace("-", "+").replace("_", "/")
            prefix = base64.b64decode(sample + "=" * ((-len(sample)) % 4))
            signature = ("png" if prefix.startswith(bytes([137,80,78,71,13,10,26,10])) else
                         "jpeg" if prefix.startswith(bytes([255,216,255])) else
                         "webp" if prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP" else
                         "gif" if prefix.startswith((b"GIF87a", b"GIF89a")) else
                         "other")
            result["base64_magic"] = signature
            result["decoded_text_form"] = (
                "xml" if prefix.startswith((b"<?xml", b"<svg", b"<SVG")) else
                "json" if prefix.startswith((b"{", b"[")) else
                "url" if prefix.startswith((b"http://", b"https://")) else
                "html" if prefix.startswith((b"<!DOCTYPE", b"<html")) else
                "other"
            )
        except (ValueError, binascii.Error):
            result["base64_magic"] = "invalid"
    return result


def safe_player_detail_shape(payload: object) -> dict:
    """Known structural keys only; never values or arbitrary response keys."""
    if type(payload) is not dict:
        return {"type": "non_object"}
    fields = ("jugador", "Jugador", "equipo", "Equipo",
              "idComponenteClub", "IdComponenteClub",
              "idTemporadaActual", "IdTemporadaActual",
              "error", "resultado", "ruta", "opcion")
    player_fields = ("id", "Id", "nombre", "Nombre", "nombreEquipo",
                     "NombreEquipo", "temporada", "Temporada",
                     "categoria", "Categoria", "partidosJugados",
                     "PartidosJugados", "puntosTotales", "PuntosTotales",
                     "Foto", "foto", "IdJugadorFoto", "idJugadorFoto")
    result = {"type": "object",
              "present": [k for k in fields if k in payload],
              "error_empty": payload.get("error") == ""}
    for key in ("jugador", "Jugador"):
        if key in payload:
            item = payload[key]
            result["player_type"] = ("object" if type(item) is dict else
                                      "array" if type(item) is list else
                                      "null" if item is None else "other")
            if type(item) is dict:
                result["player_fields"] = [k for k in player_fields if k in item]
                result["photo_fields"] = {
                    k: _image_reference_shape(item[k]) for k in
                    ("Foto", "foto", "IdJugadorFoto", "idJugadorFoto") if k in item
                }
    for key in ("equipo", "Equipo"):
        if key in payload:
            result["team_type"] = "object" if type(payload[key]) is dict else "other"
            if type(payload[key]) is dict:
                result["team_fields"] = [k for k in ("id", "Id", "nombre", "Nombre") if k in payload[key]]
    return result


def safe_statistics_shape(payload: object, kind: str) -> dict:
    """Only shape/type metadata for known APK stats fields, never raw values."""
    if type(payload) is not dict:
        return {"type": "non_object"}
    fields = (
        ("error", "resultado", "ruta", "opcion", "puntosTotalesJugador",
         "puntosMediaJugador", "asistenciasTotalesJugador",
         "faltasCometidasTotalesJugador", "rebotesTotalesJugador",
         "mostrarDatosEstadisticosAmpliados")
        if kind == "global" else
        ("error", "resultado", "ruta", "opcion", "listaDatosPartido",
         "ListaDatosPartido", "listaDatosPartidos")
    )
    out = {"type": "object", "recognized": [k for k in fields if k in payload],
           "error_empty": payload.get("error") == ""}
    for key in ("listaDatosPartido", "ListaDatosPartido", "listaDatosPartidos"):
        if key in payload:
            rows = payload[key]
            out["row_type"] = "array" if type(rows) is list else "other"
            if type(rows) is list:
                out["count"] = len(rows)
                if rows and type(rows[0]) is dict:
                    # Field names/types only. Never return any cell values.
                    allowed = (
                        "idPartido", "IdPartido", "fechaPartido", "FechaPartido",
                        "nombreEquipoRival", "NombreEquipoRival", "local", "Local",
                        "puntos", "Puntos", "asistencia", "Asistencia",
                        "faltaCometida", "FaltaCometida", "faltaRecibida", "FaltaRecibida",
                        "rebotesTotal", "RebotesTotal", "rebotesDefensivos",
                        "RebotesDefensivos", "rebotesOfensivos", "RebotesOfensivos",
                        "recuperaciones", "Recuperaciones", "perdidas", "Perdidas",
                        "valoracion", "Valoracion",
                    )
                    first = rows[0]
                    out["first_row_fields"] = [k for k in allowed if k in first]
                    out["first_row_types"] = {
                        k: ("null" if first[k] is None else
                            "bool" if type(first[k]) is bool else
                            "number" if type(first[k]) in (int, float) else
                            "string" if type(first[k]) is str else "other")
                        for k in allowed if k in first
                    }
    return out
