"""Check resource URL migration independently of a running HA instance."""
import ast
import re
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

PATH = Path(__file__).resolve().parents[1] / "custom_components/fbm/__init__.py"
MODULE = ast.parse(PATH.read_text(encoding="utf-8"))
FUNCTION = next(node for node in MODULE.body
                if getattr(node, "name", None) == "_async_register_lovelace_resource")
CONTEXT = {"HomeAssistant": object, "LOVELACE_DOMAIN": "lovelace",
           "CARD_URL": "/fbm_static/fbm-card.js", "DOMAIN": "fbm", "re": re}
ASSIGNMENTS = [node for node in MODULE.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id in
                       ("_CARD_STEM", "_VERSIONED_CARD_PATH") for target in node.targets)]
exec(compile(ast.Module(body=[*ASSIGNMENTS, FUNCTION], type_ignores=[]), str(PATH), "exec"), CONTEXT)
register = CONTEXT[FUNCTION.name]


class ResourceVersionTests(unittest.IsolatedAsyncioTestCase):
    async def test_updates_existing_resource_once(self):
        url = CONTEXT["CARD_URL"]
        item = {"id": "fbm-resource", "url": f"{url}?v=0.2.2b15"}
        update = AsyncMock(side_effect=lambda _, patch: item.update(patch))
        create = AsyncMock()
        resources = SimpleNamespace(async_load=AsyncMock(), async_items=lambda: [item],
                                    async_update_item=update, async_create_item=create)
        hass = SimpleNamespace(data={"lovelace": SimpleNamespace(resources=resources),
                                     "fbm_card_url": "/fbm_static/fbm-card.0.2.13b5.js"})
        self.assertTrue(await register(hass))
        self.assertTrue(await register(hass))
        update.assert_awaited_once_with("fbm-resource", {"url": "/fbm_static/fbm-card.0.2.13b5.js"})
        create.assert_not_awaited()
