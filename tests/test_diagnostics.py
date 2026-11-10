"""Safe FBM diagnostics tests: never return identifiers, tokens or player names."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/"custom_components/fbm/diagnostics.py"
spec=importlib.util.spec_from_file_location("fbm_diagnostics",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SafeDiagnosticsTests(unittest.TestCase):
    def test_player_detail_diagnostic_is_field_names_only(self):
        response={"error":"","Jugador":{"Id":"sensitive-id","Nombre":"Private Name",
                     "Foto":"private-image"},"IdTemporadaActual":"secret-season",
                  "key":"secret"}
        result=mod.safe_player_detail_shape(response)
        self.assertIn("Jugador",result["present"])
        self.assertIn("Id",result["player_fields"])
        for value in ("sensitive-id","Private Name","private-image","secret-season"):
            self.assertNotIn(value,str(result))

    def test_player_team_field_names_only(self):
        data={"error":"","jugador":{"Id":"p","Nombre":"Person"},
              "equipo":{"Id":"secret-team","Nombre":"Secret Team"}}
        shape=mod.safe_player_detail_shape(data)
        self.assertEqual(shape["team_fields"],["Id","Nombre"])
        self.assertNotIn("secret-team",str(shape))
        self.assertNotIn("Secret Team",str(shape))

    def test_match_field_shape_without_names_or_stat_values(self):
        payload={"error":"","listaDatosPartido":[
            {"IdPartido":"private-match","Puntos":42,
             "NombreEquipoRival":"Private Club","FaltaCometida":3}]}
        shape=mod.safe_statistics_shape(payload,"matches")
        self.assertEqual(shape["count"],1)
        self.assertIn("IdPartido",shape["first_row_fields"])
        self.assertEqual(shape["first_row_types"]["Puntos"],"number")
        for private in ("private-match","Private Club","42"):
            self.assertNotIn(private,str(shape))

    def test_photo_diagnostic_reports_format_never_photo_or_url(self):
        payload={"error":"","misjugadores":[
            {"Id":"private-id","Nombre":"Private Name",
             "Foto":"https://appaficionfbm.gesdeportiva.es/imagenes.ashx?key=private"}
        ]}
        result=mod.safe_payload_shape(payload,kind="roster")
        self.assertEqual(result["player_photo_reference"],"https_url")
        self.assertNotIn("private-id",str(result))
        self.assertNotIn("private",str(result))
        self.assertEqual(mod._image_reference_kind("opaque_photo_ref"),"opaque_reference")
        self.assertEqual(mod._image_reference_kind(""),"empty")
        self.assertEqual(mod._image_reference_kind("/images/player.png"),"relative_path")
        self.assertEqual(mod._image_reference_kind("player.jpg"),"image_filename")
        self.assertNotIn("player.jpg",str(result))

    def test_fixture_crest_diagnostic_reports_keys_only(self):
        payload={"error":"","partidos":[
            {"IdEquipoLocal":"private-local","EscudoLocal":"private-crest","ImgEquipoLocal":"private-img",
             "IdEquipoVisitante":"private-away","EscudoVisitante":None}]}
        result=mod.safe_payload_shape(payload,kind="schedule")
        self.assertIn("EscudoLocal",result["match_image_fields"])
        self.assertEqual(result["match_image_types"]["EscudoLocal"]["kind"],"opaque_reference")
        self.assertEqual(result["match_image_types"]["EscudoVisitante"]["kind"],"null")
        self.assertEqual(result["match_image_types"]["ImgEquipoLocal"]["kind"],"opaque_reference")
        for value in ("private-local","private-away","private-crest"):
            self.assertNotIn(value,str(result))

    def test_photo_format_probe_reports_structure_not_photo_contents(self):
        import base64
        opaque = base64.b64encode(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>").decode()
        info = mod._image_reference_shape(opaque)
        self.assertEqual(info["text_form"], "base64")
        self.assertEqual(info["decoded_text_form"], "xml")
        self.assertNotIn(opaque, str(info))
        self.assertNotIn("http://www.w3.org", str(info))
        jsoninfo = mod._image_reference_shape('{"photo":"private"}')
        self.assertEqual(jsoninfo["text_form"],"json")
        self.assertNotIn("private",str(jsoninfo))

    def test_stats_shape_never_returns_private_values(self):
        response={"error":"","puntosTotalesJugador":19,"key":"secret",
                  "listaDatosPartido":[{"idPartido":"private-id","puntos":5}]}
        global_shape=mod.safe_statistics_shape(response,"global")
        matches_shape=mod.safe_statistics_shape(response,"matches")
        self.assertIn("puntosTotalesJugador",global_shape["recognized"])
        self.assertEqual(matches_shape["count"],1)
        for text in ("secret","private-id","19"):
            self.assertNotIn(text,str(global_shape)+str(matches_shape))

    def test_roster_shape_never_returns_private_values(self):
        raw={"error":"secret session error", "key":"token", "misJugadores":[
            {"id":"veryprivateid","nombre":"Private Student","puntosTotales":18,
             "foto":"private-image"}]}
        result=mod.safe_payload_shape(raw,kind="roster")
        self.assertEqual(result["misJugadores_count"],1)
        self.assertTrue(result["error_type"]=="str")
        self.assertFalse(result["error_empty_string"])
        self.assertIn("nombre",result["first_row_present"])
        self.assertEqual(result["first_row_types"]["nombre"], "string")
        self.assertEqual(result["first_row_types"]["puntosTotales"], "number")
        for private in ("secret","token","Private Student","veryprivateid","private-image"):
            self.assertNotIn(private,str(result))

    def test_lowercase_roster_field_shapes_do_not_expose_values(self):
        raw={"error":"","misjugadores":[{"idJugador":"private123",
               "nombreCompleto":"Persona privada", "partidosJugados":10,
               "ficha":{"secreto":"dato interno"}, "key":"secret"}]}
        result=mod.safe_payload_shape(raw,kind="roster")
        self.assertEqual(result["misjugadores_count"],1)
        self.assertIn("idJugador",result["first_row_keys"])
        self.assertEqual(result["first_row_types"]["ficha"],"object")
        self.assertNotIn("key",result["first_row_keys"])
        for private in ("private123","Persona privada","dato interno","secret"):
            self.assertNotIn(private,str(result))

    def test_schedule_shape_only_known_keys(self):
        response={"error":"","partidos":[{"idPartido":"private-id"}],
                  "authorization":"secret-key"}
        result=mod.safe_payload_shape(response,kind="schedule")
        self.assertEqual(result["partidos_count"],1)
        self.assertEqual(result["present"],["error","partidos"])
        self.assertEqual(result["top_level_keys"],["error","partidos"])
        self.assertNotIn("authorization",str(result))

    def test_safe_top_level_field_names_include_unknown_shape_but_no_values(self):
        response={"error":"","misDatosJugadores":{"secret":"Do not expose"},"session":"secret"}
        result=mod.safe_payload_shape(response,kind="roster")
        self.assertIn("misDatosJugadores",result["top_level_keys"])
        self.assertNotIn("session",result["top_level_keys"])
        self.assertNotIn("Do not expose",str(result))

    def test_transport_categories_are_fixed(self):
        class Transport(RuntimeError):
            code="http_non_200"
        self.assertEqual(mod.safe_error_category(Transport("token=sensitive")),"http_non_200")

    def test_diagnostic_errors_do_not_expose_exceptions(self):
        result=mod.safe_error_category(RuntimeError("key=secret"))
        self.assertEqual(result,"request_failed")
        self.assertNotIn("secret",result)


if __name__=="__main__":unittest.main()
