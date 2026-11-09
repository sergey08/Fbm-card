"""Response-schema-only diagnostics: no credentials or sports-personal payloads."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "custom_components/fbm/schedule_probe.py"
spec = importlib.util.spec_from_file_location("schedule_probe", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ScheduleProbeTests(unittest.TestCase):
    def test_observed_legacy_shape(self):
        payload = {"error": "", "jornadaActual": 3,
                   "partidos": [{"IdPartido": "m", "NombreEquipoLocal": "private-team"}],
                   "key": "secret-session"}
        result = mod.summarize_schedule_shape(payload)
        self.assertEqual(result["counts"]["partidos"], 1)
        self.assertIn("IdPartido", result["entry_fields"])
        self.assertNotIn("private-team", str(result))
        self.assertNotIn("secret-session", str(result))

    def test_alternative_nested_jornadas_is_reported_not_assumed(self):
        result = mod.summarize_schedule_shape({
            "error": "", "jornadas": [{"idJornada": "x", "partidos": []}]})
        self.assertEqual(result["counts"], {"jornadas": 1})
        self.assertEqual(result["entry_fields"], ["idJornada", "partidos"])

    def test_apk_camelcase_fields_reported_without_values(self):
        payload = {"error": "", "jornadaActual": 4, "partidos": [
            {"idPartido": "private-id", "nombreEquipoLocal": "name-local",
             "nombreEquipoVisitante": "name-visitor",
             "numeroJornada": 5, "resultados": {"resultadoLocal": "41"}}
        ]}
        result = mod.summarize_schedule_shape(payload)
        self.assertEqual(result["counts"]["partidos"], 1)
        self.assertIn("idPartido", result["entry_fields"])
        self.assertIn("nombreEquipoLocal", result["entry_fields"])
        self.assertNotIn("private-id", str(result))
        self.assertNotIn("name-local", str(result))

    def test_private_error_text_never_leaks(self):
        result = mod.summarize_schedule_shape({
            "error": "private-identity", "resultado": {"token": "secret"}})
        self.assertTrue(result["has_error"])
        self.assertNotIn("private", str(result))
        self.assertNotIn("secret", str(result))

    def test_non_object_does_not_expose_contents(self):
        result = mod.summarize_schedule_shape(["sensitive"])
        self.assertEqual(result["shape"], "not_object")
        self.assertNotIn("sensitive", str(result))

if __name__ == "__main__":
    unittest.main()
