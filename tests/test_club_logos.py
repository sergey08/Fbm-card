import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("club_logos", Path(__file__).resolve().parents[1] / "custom_components/fbm/club_logos.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

HTML = '''<select id="other"><option value="999">Club A</option></select>
<select id="contenedor_filtros_DDLClub"><option value="0">Todos</option>
<option value="6419">PINTOBASKET E.C.B.</option>
<option value="6892">VILLA DE VALDEMORO C.B.</option>
<option value="3">Duplicado</option><option value="4">DUPLICADO</option>
<option value="../../bad">Peligro</option></select>'''


def run(coro):
    try:
        coro.send(None)
    except StopIteration as done:
        return done.value
    raise AssertionError("Unexpected suspension")


class CatalogTests(unittest.TestCase):
    def setUp(self):
        async def immediate(function):
            return function()
        patcher = patch.object(module.asyncio, "to_thread", immediate)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_exact_matches_cache_and_ambiguity(self):
        calls = []
        def fetch():
            calls.append(1)
            return module.parse_catalog(HTML)
        cat = module.ClubLogoCatalog(fetch=fetch, clock=lambda: 1)
        self.assertEqual(run(cat.logo(" pintobasket E.C.B. ")), module.IMAGE_URL.format("6419"))
        self.assertEqual(run(cat.logo("VILLA DE VALDEMORO C.B.")), module.IMAGE_URL.format("6892"))
        self.assertEqual(run(cat.logo("PINTOBASKET")), "")
        self.assertEqual(run(cat.logo("Duplicado")), "")
        self.assertEqual(run(cat.logo("Peligro")), "")
        self.assertEqual(len(calls), 1)

    def test_failure_is_nonfatal_and_negative_cached(self):
        calls = []
        def fail():
            calls.append(1)
            raise OSError("offline")
        cat = module.ClubLogoCatalog(fetch=fail, clock=lambda: 1)
        self.assertEqual(run(cat.logo("Club")), "")
        self.assertEqual(run(cat.logo("Club")), "")
        self.assertEqual(len(calls), 1)

    def test_refresh_after_expiry(self):
        now = [1]
        calls = []
        def fetch():
            calls.append(1)
            return {"club": str(len(calls))}
        cat = module.ClubLogoCatalog(fetch=fetch, clock=lambda: now[0])
        self.assertEqual(run(cat.logo("Club")), module.IMAGE_URL.format("1"))
        now[0] += 86401
        self.assertEqual(run(cat.logo("Club")), module.IMAGE_URL.format("2"))


