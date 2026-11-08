"""Pruebas aisladas del gestor de consultas FBM, sin red."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fbm"
for name in ("custom_components", "custom_components.fbm"):
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = [str(ROOT)]
        sys.modules[name] = module
spec = importlib.util.spec_from_file_location("custom_components.fbm.queries", ROOT / "queries.py")
queries = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = queries
spec.loader.exec_module(queries)


class Adapter:
    def __init__(self):
        self.calls = 0

    async def query(self, kind, identifiers):
        self.calls += 1
        await asyncio.sleep(0)
        return {"fuente": "FBM", "tipo": kind, "ids": identifiers}


class QueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_requests_use_one_adapter_call(self):
        adapter = Adapter()
        service = queries.FBMQueries(adapter)
        results = await asyncio.gather(*(service.query("jornada", grupo=4, jornada=2) for _ in range(5)))
        self.assertEqual(adapter.calls, 1)
        self.assertTrue(all(x == results[0] for x in results))

    async def test_waiting_requests_keep_single_lock(self):
        started = asyncio.Event()
        release = asyncio.Event()

        class SlowAdapter:
            def __init__(self):
                self.calls = 0

            async def query(self, kind, identifiers):
                self.calls += 1
                started.set()
                await release.wait()
                return {"fuente": "FBM", "ids": identifiers}

        adapter = SlowAdapter()
        service = queries.FBMQueries(adapter)
        first = asyncio.create_task(service.query("partido", partido=123))
        await started.wait()
        others = [asyncio.create_task(service.query("partido", partido=123))
                  for _ in range(8)]
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, *others)
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(service._locks, {})
        self.assertEqual(service._waiters, {})

    async def test_cache_returns_defensive_copy(self):
        adapter = Adapter()
        service = queries.FBMQueries(adapter)
        first = await service.query("equipo", equipo=42)
        first["ids"]["equipo"] = 999
        second = await service.query("equipo", equipo=42)
        self.assertEqual(second["ids"]["equipo"], 42)
        self.assertEqual(adapter.calls, 1)

    async def test_invalid_kind_rejected(self):
        with self.assertRaises(queries.FBMQueryError):
            await queries.FBMQueries(Adapter()).query("admin", equipo=1)

    async def test_missing_source_rejected(self):
        class Invalid:
            async def query(self, kind, identifiers):
                return {"resultado": "sin procedencia"}
        with self.assertRaises(queries.FBMQueryError):
            await queries.FBMQueries(Invalid()).query("partido", partido=1)


if __name__ == "__main__":
    unittest.main()
