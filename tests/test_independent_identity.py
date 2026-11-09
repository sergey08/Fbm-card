"""Pruebas de persistencia simulada sin red ni Home Assistant."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

path = Path(__file__).resolve().parents[1] / 'custom_components/fbm/independent_identity.py'
spec = importlib.util.spec_from_file_location('independent_identity_test', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class MemoryStore:
    def __init__(self, data=None): self.data, self.saves = data, 0
    async def async_load(self): return copy.deepcopy(self.data)
    async def async_save(self, value): self.data, self.saves = copy.deepcopy(value), self.saves + 1


def run_immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    raise AssertionError('La operacion simulada no deberia suspenderse')


class IndependentIdentityTests(unittest.TestCase):
    def test_create_reload_and_bind_without_replacing_uid(self):
        backend = MemoryStore()
        manager = module.IndependentIdentityStore(backend)
        self.assertIsNone(run_immediate(manager.async_load()))
        self.assertEqual(backend.saves, 0)
        created = run_immediate(manager.async_create())
        self.assertRegex(created.uid, r'^[0-9a-f]{16}$')
        self.assertNotIn(created.uid, repr(created))
        reloaded = run_immediate(module.IndependentIdentityStore(backend).async_load())
        self.assertEqual(reloaded, created)
        bound = run_immediate(manager.async_bind_candidate(created.uid, 'candidate'))
        self.assertEqual(bound.candidate_device_id, 'candidate')
        self.assertNotIn('candidate', repr(bound))
        self.assertEqual(backend.data['uid'], created.uid)
        self.assertNotIn('key', backend.data)
        self.assertEqual(backend.saves, 2)
        run_immediate(manager.async_bind_candidate(created.uid, 'candidate'))
        self.assertEqual(backend.saves, 2)
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_create())
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_bind_candidate(created.uid, 'other'))
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_bind_candidate('other-uid', 'candidate'))
        self.assertEqual(backend.saves, 2)

    def test_corrupt_and_missing_identity_never_overwritten(self):
        backend = MemoryStore({'format': 1, 'uid': 'bad', 'candidate_device_id': None})
        manager = module.IndependentIdentityStore(backend)
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_load())
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_create())
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_bind_candidate('bad', 'device'))
        self.assertEqual(backend.saves, 0)
        empty = module.IndependentIdentityStore(MemoryStore())
        with self.assertRaises(module.IdentityError): run_immediate(empty.async_bind_candidate('uid', 'device'))

    def test_existing_file_with_empty_load_is_not_replaced(self):
        backend = MemoryStore()
        async def exists(): return True
        manager = module.IndependentIdentityStore(backend, async_exists=exists)
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_load())
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_create())
        self.assertEqual(backend.saves, 0)

    def test_legacy_without_candidate_is_treated_as_pending(self):
        backend = MemoryStore({'format': 1, 'uid': '0123456789abcdef', 'candidate_device_id': None})
        manager = module.IndependentIdentityStore(backend)
        self.assertEqual(run_immediate(manager.async_load()).registration_state, 'pending')
        with self.assertRaises(module.IdentityError): run_immediate(manager.async_begin_registration())
        self.assertEqual(backend.saves, 0)
