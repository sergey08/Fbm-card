"""Pruebas del inspector seguro de esquemas FBM."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "scripts/inspeccionar_respuesta_fbm.py"
spec = importlib.util.spec_from_file_location("inspector_fbm", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InspectorTests(unittest.TestCase):
    def test_no_expose_sensitive_values(self):
        result = module.describe({
            "id_dispositivo": "privado",
            "key": "secreto",
            "resultado": "ok",
            "equipos": [{"nombre": "Equipo privado", "id": 7}],
        })
        serialized = str(result)
        self.assertNotIn("privado", serialized)
        self.assertNotIn("secreto", serialized)
        self.assertNotIn("Equipo privado", serialized)
        self.assertIn("equipos", serialized)

    def test_limits_depth(self):
        value = {"a": {"b": {"c": {"d": {"e": "oculto"}}}}}
        self.assertNotIn("oculto", str(module.describe(value)))


if __name__ == "__main__":
    unittest.main()
