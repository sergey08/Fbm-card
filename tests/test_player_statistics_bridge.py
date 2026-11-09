"""Statistics workflow is opt-in and refuses network after unsafe binding."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock

ROOT=Path(__file__).resolve().parents[1]/"custom_components/fbm"
pkg=types.ModuleType("fbm_statistics_bridge_test")
pkg.__path__=[str(ROOT)]
sys.modules[pkg.__name__]=pkg
for name in ("player_context","player_protocol","player_statistics","player_statistics_bridge"):
    spec=importlib.util.spec_from_file_location(pkg.__name__+"."+name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
mod=sys.modules[pkg.__name__+".player_statistics_bridge"]


def detail():
    return {"error":"","jugador":{"id":"p"},"equipo":{"id":"t"},
            "idComponenteClub":"c","idTemporadaActual":"season"}

class StatsBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_network_stats_on_unverified_player_team_binding(self):
        raw=detail();raw["equipo"]={"id":"another"}
        fetch=AsyncMock(return_value=raw)
        post=AsyncMock()
        bridge=mod.PlayerStatisticsFetcher(fetch,post)
        with self.assertRaises(ValueError):
            await bridge.fetch("p","t","device","key")
        fetch.assert_awaited_once_with("p")
        post.assert_not_awaited()

    async def test_verified_flow_uses_two_apk_actions_exactly(self):
        fetch=AsyncMock(return_value=detail())
        post=AsyncMock(side_effect=[
            {"error":"","puntosTotalesJugador":12},
            {"error":"","listaDatosPartido":[{"idPartido":"m","puntos":"12"}]}
        ])
        bridge=mod.PlayerStatisticsFetcher(fetch,post)
        result=await bridge.fetch("p","t","device","key")
        self.assertEqual(result["globales"]["estadisticas"]["puntos_totales"],12)
        self.assertEqual(result["partidos"]["partidos"][0]["puntos"],12)
        self.assertEqual(post.await_count,2)
        actions=[call.args[0]["accion"] for call in post.await_args_list]
        self.assertEqual(actions,["datosGlobalesJugadorEquipo","datosMediasJugadorPartidos"])
        for call in post.await_args_list:
            fields=call.args[0]
            self.assertEqual(fields["id_componente_club"],"c")
            self.assertEqual(fields["id_temporada"],"season")
            self.assertEqual(fields["id_equipo"],"t")
        self.assertNotIn("key",result)

    async def test_invalid_global_response_blocks_match_request(self):
        post=AsyncMock(return_value={"error":"failed"})
        bridge=mod.PlayerStatisticsFetcher(AsyncMock(return_value=detail()),post)
        with self.assertRaises(ValueError):
            await bridge.fetch("p","t","device","key")
        self.assertEqual(post.await_count,1)
if __name__=="__main__":unittest.main()
