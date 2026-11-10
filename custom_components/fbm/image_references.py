"""Validate official FBM inline image data, without external URLs or guesses.

Only bounded verified PNG/JPEG/WebP bytes are accepted (base64, hex, or hex/UTF-16LE/base64).
Invalid, unsupported or large references are quietly omitted.
"""
from __future__ import annotations
import base64
import binascii
import re

_BASE64 = re.compile(r"^[A-Za-z0-9+/]*={0,2}$")
_ALLOWED_PREFIX = re.compile(r"^data:image/(png|jpeg|jpg|webp);base64,", re.IGNORECASE)


def image_data_uri(value: object, *, max_bytes: int = 131072) -> str | None:
    if type(value) is not str or not value or len(value) > 2 * max_bytes + 128:
        return None
    text = value.strip()
    prefix = _ALLOWED_PREFIX.match(text)
    if prefix:
        text = text[prefix.end():]
    # FBM image references can be encoded. Accept hex only if it decodes
    # directly to a recognized image; never decode URLs or opaque IDs.
    if text and len(text) % 2 == 0 and re.fullmatch(r"[0-9a-fA-F]+", text):
        try:
            raw = bytes.fromhex(text)
        except ValueError:
            return None
        # Some FBM references contain hex(UTF-16LE(base64(image))).
        # Only unwrap this specific encoding and only accept an actual
        # image signature below. Never turn opaque references into URLs.
        if (len(raw) % 2 == 0 and len(raw) >= 16
                and all(raw[i] == 0 for i in range(1, min(len(raw), 48), 2))):
            try:
                inner = raw.decode("utf-16le", errors="strict").strip()
                if (len(inner) <= 4 * max_bytes // 3 + 4 and len(inner) % 4 == 0
                        and _BASE64.fullmatch(inner)):
                    raw = base64.b64decode(inner, validate=True)
            except (UnicodeError, ValueError, binascii.Error):
                return None
    else:
        if not text or len(text) % 4 != 0 or not _BASE64.fullmatch(text):
            return None
        try:
            raw = base64.b64decode(text, validate=True)
        except (ValueError, binascii.Error):
            return None
    if not raw or len(raw) > max_bytes:
        return None
    mime = None
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif raw.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        mime = "image/webp"
    if not mime:
        return None
    return "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")


# APK Afición FBM 5.0.42: static base URL in
# Lcom/google/android/gms/internal/play_billing/r0;.a, and image
# composable LR4/o;.t assembles ?tipo=jugador&id=<Foto>.
_OFFICIAL_PLAYER_IMAGE_BASE = "https://appaficionfbm.gesdeportiva.es/imagenes.ashx?tipo=jugador&id="


def official_player_image_url(value: object) -> str | None:
    """Resolve only a bounded opaque *official* FBM photo reference.

    The APK passes JugadorEquipoDto.Foto unchanged to the official image
    composable. Do not decode it as pixels, use player IDs, accept external
    hosts or emit private values into logs.
    """
    if type(value) is not str or not (16 <= len(value) <= 4096):
        return None
    if len(value) % 2 or re.fullmatch(r"[0-9a-fA-F]+", value) is None:
        return None
    return _OFFICIAL_PLAYER_IMAGE_BASE + value
