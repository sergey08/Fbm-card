"""Comprobar que el adaptador único no consulta datos sin acceso validado."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fbm/aficion_adapter.py"
spec = importlib.util.spec_from_file_location("fbm_aficion_adapter", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_unvalidated_access(self):
        adapter = module.AficionFBMAdapter()
        with self.assertRaises(module.FBMAccessNotValidated):
            await adapter.query("jornada", {"competicion": 1, "grupo": 2, "jornada": 3})


if __name__ == "__main__":
    unittest.main()
