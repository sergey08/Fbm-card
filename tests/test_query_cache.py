"""Pruebas aisladas de caché TTL sin acceso a Internet."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fbm/query_cache.py"
spec = importlib.util.spec_from_file_location("fbm_query_cache", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.time = 100.0
        self.cache = module.QueryCache(ttl_seconds=10, max_entries=2, clock=lambda: self.time)

    def test_hit_and_expiration(self):
        self.cache.put(("jornada", 3), {"partidos": [1]})
        self.assertEqual(self.cache.get(("jornada", 3)), {"partidos": [1]})
        self.time = 110.0
        self.assertIsNone(self.cache.get(("jornada", 3)))

    def test_defensive_copy(self):
        original = {"partidos": [1]}
        self.cache.put(("jornada", 3), original)
        original["partidos"].append(2)
        received = self.cache.get(("jornada", 3))
        received["partidos"].append(3)
        self.assertEqual(self.cache.get(("jornada", 3)), {"partidos": [1]})

    def test_lru_eviction(self):
        self.cache.put(("jornada", 1), 1)
        self.cache.put(("jornada", 2), 2)
        self.cache.get(("jornada", 1))
        self.cache.put(("jornada", 3), 3)
        self.assertIsNone(self.cache.get(("jornada", 2)))
        self.assertEqual(self.cache.get(("jornada", 1)), 1)

    def test_custom_ttl(self):
        self.cache.put(("partido", 1), 10, ttl_seconds=2)
        self.time += 3
        self.assertIsNone(self.cache.get(("partido", 1)))

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            module.QueryCache(ttl_seconds=0)
        with self.assertRaises(ValueError):
            module.QueryCache(max_entries=0)
        with self.assertRaises(ValueError):
            self.cache.put("clave", {})


if __name__ == "__main__":
    unittest.main()
