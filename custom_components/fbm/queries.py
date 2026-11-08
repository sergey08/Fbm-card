"""Consultas FBM bajo demanda con caché; sin acceso a red integrado.

El adaptador se inyectará únicamente tras validar el acceso oficial a FBM.
No hay datos ficticios ni credenciales de la aplicación.
"""
import asyncio
from copy import deepcopy

from .query_cache import QueryCache


class FBMQueryError(ValueError):
    """Solicitud o respuesta inválida."""


class FBMQueries:
    """Interfaz común para tarjeta, entidades y futuras herramientas MCP."""

    ALLOWED = frozenset({"jornadas", "jornada", "partido", "equipo", "clasificacion"})
    TTL = {"jornadas": 3600, "jornada": 300, "partido": 60,
           "equipo": 300, "clasificacion": 300}

    def __init__(self, adapter, *, cache=None):
        # adapter.query(kind, identifiers) es una corrutina; el adaptador
        # debe verificar procedencia y permisos de acceso.
        self._adapter = adapter
        self._cache = cache if cache is not None else QueryCache()
        self._locks = {}
        self._waiters = {}
        self._guard = asyncio.Lock()

    async def query(self, kind: str, **identifiers):
        """Consultar FBM y devolver copia de un objeto validado.

        Nunca se responde con datos obsoletos tras caducar la caché.
        """
        if kind not in self.ALLOWED:
            raise FBMQueryError("Tipo de consulta no permitido")
        if not identifiers or len(identifiers) > 5:
            raise FBMQueryError("Se requieren identificadores oficiales")
        for name, value in identifiers.items():
            if (not isinstance(name, str) or not name.isidentifier()
                    or type(value) not in (str, int)
                    or isinstance(value, str) and (not value.strip() or len(value) > 128)
                    or isinstance(value, int) and value < 0):
                raise FBMQueryError("Identificador inválido")
        key = (kind,) + tuple(f"{k}={v}" for k, v in sorted(identifiers.items()))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        async with self._guard:
            lock = self._locks.setdefault(key, asyncio.Lock())
            self._waiters[key] = self._waiters.get(key, 0) + 1
        try:
            async with lock:
                cached = self._cache.get(key)
                if cached is not None:
                    return cached
                result = await self._adapter.query(kind, dict(identifiers))
                if not isinstance(result, dict):
                    raise FBMQueryError("Respuesta oficial no válida")
                if result.get("fuente") != "FBM":
                    raise FBMQueryError("Falta la procedencia FBM declarada")
                # La etiqueta de fuente NO autentica el origen: el adaptador
                # debe validar el endpoint real antes de devolver datos.
                self._cache.put(key, result, ttl_seconds=self.TTL[kind])
                return deepcopy(result)
        finally:
            async with self._guard:
                self._waiters[key] -= 1
                if self._waiters[key] == 0:
                    self._waiters.pop(key, None)
                    self._locks.pop(key, None)

    def clear(self):
        self._cache.clear()
