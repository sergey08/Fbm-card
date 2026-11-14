"""Regression tests for first-use guest onboarding without Home Assistant runtime."""
import ast
import asyncio
from pathlib import Path
import sys
import types
import unittest


def load_guest_method():
    path = Path(__file__).resolve().parents[1] / "custom_components/fbm/config_flow.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "FBMCompetitionOptionsFlow")
    method = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef)
                  and node.name == "async_step_guest")
    code = compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec")
    namespace = {}
    exec(code, namespace)
    return namespace["async_step_guest"]


class FakeClient:
    def __init__(self, status):
        self.status = dict(status)
        self.calls = []

    async def async_status(self):
        return dict(self.status)

    async def async_create_identity(self):
        self.calls.append("create")
        self.status["identidad_creada"] = True

    async def async_register(self, release):
        self.calls.append(("register", release))
        self.status["candidato_guardado"] = True

    async def async_recover_registration(self, release):
        self.calls.append(("recover", release))
        self.status["registro_pendiente"] = False
        self.status["candidato_guardado"] = True

    async def async_connect(self, release):
        self.calls.append(("connect", release))
        self.status["sesion_vigente"] = True


class GuestFlowTests(unittest.TestCase):
    def setUp(self):
        self.previous = sys.modules.get("probatio")
        probatio = types.ModuleType("probatio")
        probatio.Required = lambda name, default=None: name
        probatio.Schema = lambda schema: schema
        sys.modules["probatio"] = probatio

    def tearDown(self):
        if self.previous is None:
            sys.modules.pop("probatio", None)
        else:
            sys.modules["probatio"] = self.previous

    def flow(self, client):
        class Flow:
            async_step_guest = load_guest_method()

            def _entry(self):
                return {"cliente_independiente": client}

            def async_show_form(self, **kwargs):
                return kwargs

            async def async_step_search(self):
                return {"step_id": "search_ready"}

        return Flow()

    def test_fresh_install_requires_consent(self):
        client = FakeClient({"identidad_creada": False, "candidato_guardado": False,
                             "registro_pendiente": False, "sesion_vigente": False})
        flow = self.flow(client)
        result = asyncio.run(flow.async_step_guest())
        self.assertEqual(result["step_id"], "guest")
        self.assertEqual(client.calls, [])
        result = asyncio.run(flow.async_step_guest({"autorizar": True}))
        self.assertEqual(result["step_id"], "search_ready")
        self.assertEqual(client.calls, ["create", ("register", "16"), ("connect", "16")])

    def test_pending_registration_requires_consent_then_recovers(self):
        client = FakeClient({"identidad_creada": True, "candidato_guardado": False,
                             "registro_pendiente": True, "sesion_vigente": False})
        flow = self.flow(client)
        result = asyncio.run(flow.async_step_guest())
        self.assertEqual(result["errors"]["base"], "registration_pending")
        self.assertEqual(client.calls, [])
        result = asyncio.run(flow.async_step_guest({"autorizar": True}))
        self.assertEqual(result["step_id"], "search_ready")
        self.assertEqual(client.calls, [("recover", "16"), ("connect", "16")])

    def test_existing_candidate_only_connects(self):
        client = FakeClient({"identidad_creada": True, "candidato_guardado": True,
                             "registro_pendiente": False, "sesion_vigente": False})
        result = asyncio.run(self.flow(client).async_step_guest({"autorizar": True}))
        self.assertEqual(result["step_id"], "search_ready")
        self.assertEqual(client.calls, [("connect", "16")])

    def test_active_session_does_not_register(self):
        client = FakeClient({"identidad_creada": True, "candidato_guardado": True,
                             "registro_pendiente": False, "sesion_vigente": True})
        result = asyncio.run(self.flow(client).async_step_guest())
        self.assertEqual(result["step_id"], "search_ready")
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
