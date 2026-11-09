"""Safe inspection tests with synthetic official-response shapes."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components/fbm/season_evidence.py"
spec = importlib.util.spec_from_file_location("season_evidence", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def response():
    return {
        "error": "", "faseActual": "phase1", "grupoActual": "group1",
        "listaFasesGrupo": [{"IdFase": "phase1", "TipoFase": "LIGA",
            "Grupos": [{"IdGrupo": "group1", "NombreGrupo": "Grupo"}]}]}


class SeasonEvidenceTests(unittest.TestCase):
    def test_absent_metadata_never_claims_verification(self):
        evidence = module.inspect_season_evidence(response(), "phase1", "group1")
        self.assertEqual(evidence["season_candidates"], [])
        self.assertEqual(evidence["season_evidence_status"], "none")
        self.assertFalse(evidence["season_verified"])

    def test_allowlisted_top_level_candidate_is_unverified(self):
        payload = response()
        payload["idTemporadaActual"] = 55
        payload["key"] = "private-key"
        evidence = module.inspect_season_evidence(payload, "phase1", "group1")
        self.assertEqual(evidence["season_candidates"], [
            {"scope": "response", "field": "idTemporadaActual", "candidate": "55"}])
        self.assertFalse(evidence["season_verified"])
        self.assertNotIn("private-key", repr(evidence))

    def test_conflicting_phase_and_group_candidates(self):
        payload = response()
        payload["listaFasesGrupo"][0]["IdTemporada"] = "42"
        payload["listaFasesGrupo"][0]["Grupos"][0]["id_temporada"] = "43"
        evidence = module.inspect_season_evidence(payload, "phase1", "group1")
        self.assertEqual(evidence["season_evidence_status"], "conflicting")
        self.assertFalse(evidence["season_verified"])

    def test_unrelated_phase_and_group_data_ignored(self):
        payload = response()
        payload["listaFasesGrupo"].append(
            {"IdFase": "other", "id_temporada": "secret",
             "Grupos": [{"IdGrupo": "group1", "IdTemporada": "123"}]})
        payload["listaFasesGrupo"][0]["Grupos"].append(
            {"IdGrupo": "other", "IdTemporada": "999"})
        evidence = module.inspect_season_evidence(payload, "phase1", "group1")
        self.assertEqual(evidence["season_candidates"], [])

    def test_rejects_ambiguous_or_error_response(self):
        payload = response()
        payload["listaFasesGrupo"].append(payload["listaFasesGrupo"][0])
        with self.assertRaises(ValueError):
            module.inspect_season_evidence(payload, "phase1", "group1")
        with self.assertRaises(ValueError):
            module.inspect_season_evidence({"error": "denied"}, "phase1", "group1")

    def test_does_not_accept_boolean_or_oversized_candidates(self):
        payload = response()
        payload["IdTemporada"] = True
        payload["listaFasesGrupo"][0]["id_temporada"] = "A" * 500
        evidence = module.inspect_season_evidence(payload, "phase1", "group1")
        self.assertEqual(evidence["season_candidates"], [])

if __name__ == "__main__":
    unittest.main()
