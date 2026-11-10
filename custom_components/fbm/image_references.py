"""Validate official FBM inline image data, without external URLs or guesses.

Only bounded, base64-encoded PNG/JPEG/WebP image content is accepted.
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
