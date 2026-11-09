"""Catálogo público FBM TV: correspondencia conservadora de clubes a escudos."""
from __future__ import annotations

import asyncio
from html.parser import HTMLParser
from time import monotonic
import urllib.request

CATALOG_URL = "https://fbmtv.fbm.es/es/archivo"
IMAGE_URL = "https://fbmtv.fbm.es/imagenes/equipos/escudo-{}.jpg"
MAX_BYTES = 2_000_000


def _name(value):
    return " ".join(value.split()).casefold()


class _ClubParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_select = False
        self.option = None
        self.matches = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select" and attrs.get("id") == "contenedor_filtros_DDLClub":
            self.in_select = True
        elif self.in_select and tag == "option":
            value = attrs.get("value", "")
            self.option = [value, ""] if value.isascii() and value.isdigit() and 0 < len(value) <= 10 else None

    def handle_data(self, data):
        if self.option is not None:
            self.option[1] += data

    def handle_endtag(self, tag):
        if tag == "option" and self.option is not None:
            identifier, name = self.option
            key = _name(name)
            if key:
                self.matches.setdefault(key, set()).add(identifier)
            self.option = None
        elif tag == "select" and self.in_select:
            self.in_select = False


def parse_catalog(html):
    parser = _ClubParser()
    parser.feed(html)
    return {name: next(iter(ids)) for name, ids in parser.matches.items() if len(ids) == 1}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _download():
    opener = urllib.request.build_opener(_NoRedirect())
    request = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "FBM-Card/0.1 (Home Assistant)"})
    with opener.open(request, timeout=10) as response:
        if response.headers.get_content_type() != "text/html":
            raise ValueError("Contenido no válido")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("Catálogo demasiado grande")
        charset = response.headers.get_content_charset() or "utf-8"
        return parse_catalog(body.decode(charset, errors="strict"))


class ClubLogoCatalog:
    """Una descarga compartida; errores no afectan a los datos deportivos."""
    def __init__(self, fetch=_download, clock=monotonic):
        self._fetch, self._clock = fetch, clock
        self._lock = asyncio.Lock()
        self._catalog = {}
        self._expires = 0

    async def logo(self, club):
        if not isinstance(club, str) or not club.strip() or len(club) > 200:
            return ""
        async with self._lock:
            if self._clock() >= self._expires:
                try:
                    catalog = await asyncio.to_thread(self._fetch)
                    if not catalog:
                        raise ValueError("Catálogo vacío")
                    self._catalog = catalog
                    self._expires = self._clock() + 86400
                except (OSError, ValueError, UnicodeError, LookupError):
                    self._expires = self._clock() + 300
            identifier = self._catalog.get(_name(club))
        return IMAGE_URL.format(identifier) if identifier else ""

