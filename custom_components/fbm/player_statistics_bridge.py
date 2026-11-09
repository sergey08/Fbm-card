"""Shared official-player statistics workflow, gated by detail DTO evidence.

This module has no HA side effects or network on construction. It is ready
for the same read path in opt-in sync and explicit non-sync cards, once
authenticated responses have been validated end to end.
"""
from __future__ import annotations

from .player_context import verified_player_stats_context
from .player_protocol import player_stats_fields
from .player_statistics import (
    normalize_global_player_stats, normalize_player_match_list
)


class PlayerStatisticsFetcher:
    """Build the two APK forms *only after* verifying the detail association.

    raw_detail(player_id) -> authorized response from /v2/jugador.ashx.
    post_statistics(fields) -> authorized response from /v2/jugador.ashx.
    The caller owns the existing guest-session scope, no new registration.
    """

    def __init__(self, raw_detail, post_statistics):
        self._raw_detail = raw_detail
        self._post_statistics = post_statistics

    async def fetch(self, player_id, team_id, device_id, key):
        detail = await self._raw_detail(player_id)
        binding = verified_player_stats_context(detail, player_id, team_id)
        global_fields = player_stats_fields(
            device_id, key, **binding, action="datosGlobalesJugadorEquipo"
        )
        global_response = await self._post_statistics(global_fields)
        global_data = normalize_global_player_stats(global_response)
        match_fields = player_stats_fields(
            device_id, key, **binding, action="datosMediasJugadorPartidos"
        )
        match_response = await self._post_statistics(match_fields)
        match_data = normalize_player_match_list(match_response)
        return {
            "jugador": player_id, "equipo": team_id,
            "globales": global_data, "partidos": match_data
        }
