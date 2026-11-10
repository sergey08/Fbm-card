"""Safe FBM diagnostics tests: never return identifiers, tokens or player names."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/"custom_components/fbm/diagnostics.py"
spec=importlib.util.spec_from_file_location("fbm_diagnostics",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SafeDiagnosticsTests(unittest.TestCase):
    def test_roster_shape_never_returns_private_values(self):
        raw={"error":"secret session error", "key":"token", "misJugadores":[
            {"id":"veryprivateid","nombre":"Private Student","puntosTotales":18,
             "foto":"private-image"}]}
        result=mod.safe_payload_shape(raw,kind="roster")
        self.assertEqual(result["misJugadores_count"],1)
        self.assertTrue(result["error_type"]=="str")
        self.assertFalse(result["error_empty_string"])
        self.assertIn("nombre",result["first_row_present"])
        for private in ("secret","token","Private Student","veryprivateid","private-image"):
            self.assertNotIn(private,str(result))

    def test_schedule_shape_only_known_keys(self):
        response={"error":"","partidos":[{"idPartido":"private-id"}],
                  "authorization":"secret-key"}
        result=mod.safe_payload_shape(response,kind="schedule")
        self.assertEqual(result["partidos_count"],1)
        self.assertEqual(result["present"],["error","partidos"])
        self.assertNotIn("authorization",str(result))

    def test_diagnostic_errors_do_not_expose_exceptions(self):
        result=mod.safe_error_category(RuntimeError("key=secret"))
        self.assertEqual(result,"request_failed")
        self.assertNotIn("secret",result)


if __name__=="__main__":unittest.main()
