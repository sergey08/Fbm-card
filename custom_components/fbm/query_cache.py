"""Caché temporal acotada para consultas oficiales bajo demanda.

No realiza consultas de red ni persiste históricos. Solo conserva respuestas
que el futuro adaptador oficial haya validado.
"""
from collections import OrderedDict
from copy import deepcopy
from time import monotonic


class QueryCache:
    """Caché LRU con caducidad y copias defensivas."""

    def __init__(self, *, ttl_seconds=300, max_entries=128, clock=monotonic):
        if not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds debe ser positivo")
        if type(max_entries) is not int or not 1 <= max_entries <= 1024:
            raise ValueError("max_entries fuera de rango")
        self._ttl = ttl_seconds
        self._limit = max_entries
        self._clock = clock
        self._entries = OrderedDict()

    def get(self, key):
        """Devolver copia de un resultado vigente o None si no existe."""
        now = self._clock()
        if key not in self._entries:
            return None
        expires, value = self._entries[key]
        if now >= expires:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return deepcopy(value)

    def put(self, key, value, *, ttl_seconds=None):
        """Guardar un resultado durante un plazo acotado."""
        if not isinstance(key, tuple) or not key or not all(isinstance(part, (str, int)) for part in key):
            raise ValueError("La clave debe ser una tupla de identificadores")
        ttl = self._ttl if ttl_seconds is None else ttl_seconds
        if not isinstance(ttl, (int, float)) or isinstance(ttl, bool) or ttl <= 0:
            raise ValueError("TTL inválido")
        self._entries[key] = (self._clock() + ttl, deepcopy(value))
        self._entries.move_to_end(key)
        while len(self._entries) > self._limit:
            self._entries.popitem(last=False)

    def clear(self):
        """Vaciar la caché al descargar o reconfigurar la integración."""
        self._entries.clear()

    def __len__(self):
        """Número de entradas, incluidas las aún no purgadas tras caducar."""
        return len(self._entries)
