# FBM archived match preview for Home Assistant MCP

## English

### Scope and security
The `fbm/competition/match_preview` WebSocket command reads **only** the existing, explicitly followed competition snapshots in SQLite. It does not call the FBM website, refresh the archive, or change database records. Home Assistant administrator permissions are required (`require_admin`). It only returns team-level standings, up to four scored games per team, prior head-to-head scores, venue and schedule, observation timestamps, and archive coverage. **Player identities and statistics are not returned.**

### Calling it through Home Assistant Tunnel HA-MCP
1. Use `ha_get_integration(query="fbm")` to obtain the loaded config entry ID.
2. Use `ha_get_state(entity_id="sensor.competiciones")` and select an explicitly followed entry from `attributes.groups`. Take `season_id`, `phase_id`, `group_id` and the exact `team_name`.
3. Call `ha_call_service` in its **WebSocket command** mode:

```json
{
  "ws_command": "fbm/competition/match_preview",
  "data": {
    "entry_id": "<config entry ID>",
    "season_id": "<group season_id>",
    "phase_id": "<group phase_id>",
    "group_id": "<group group_id>",
    "equipo": "<exact team_name>"
  }
}
```

The new command is not available until the corresponding FBM integration release is installed and Home Assistant has been restarted. No change to Home Assistant MCP itself is needed: the already-connected tunnel supports read-only custom WebSocket commands.

### Existing complementary endpoints (already tested against v0.2.2b19)
- `fbm/competition/analysis`: league-wide score averages, match counts, scoring leaders, and archived statistical coverage.
- `fbm/competition/latest` with `source="fixtures"`, `subject=""`: complete archived fixtures, venues, dates, rounds and scorelines.
- `fbm/competition/team_roster`: validated roster and matches for a team by official team ID (tested).
- `fbm/competition/team_player_stats`: player-level data, validated against the selected followed group and roster (tested).

Those administrative commands must remain protected. Do not copy junior players' personal information to public Home Assistant sensors. Use numeric sample sizes and observed timestamps in reports; missing scores and missing player statistics are unknown, **not zero**. The app's `automatic_refresh` fields remain a separate follow-up: `pending` with null `last_run` does not prove scheduled syncing.

### Validation and release gate
Unit-test empty and malformed archives, incomplete scores, team membership, next-match ordering, and historical head-to-head. Verify WS registration, administrator-only access and followed-group authorization. Run the repository's FBM tests and Home Assistant Core 2026.11 smoke suite; then test against a real administrator session in HA. Do not deploy to production or publish a beta before green CI. Update bilingual release notes and README on `main` before a stable release.

## Español

### Alcance y seguridad
El comando WebSocket `fbm/competition/match_preview` lee **únicamente** los registros SQLite de una competición expresamente seguida. No consulta FBM por Internet, no sincroniza ni modifica datos. Exige administrador de Home Assistant (`require_admin`). Devuelve clasificación de equipos, hasta cuatro partidos con marcador por equipo, precedentes, pabellón, calendario, fechas del archivo y cobertura. **No devuelve identidades ni estadísticas de jugadores.**

### Consulta mediante Home Assistant Tunnel HA-MCP
1. Consultar `ha_get_integration(query="fbm")` y recuperar el ID de la entrada activa.
2. Consultar `ha_get_state(entity_id="sensor.competiciones")`; escoger el grupo seguido y copiar sus `season_id`, `phase_id`, `group_id` y `team_name` exacto.
3. Ejecutar `ha_call_service` en modo `ws_command="fbm/competition/match_preview"` con `data` igual al ejemplo JSON anterior.

El comando nuevo solo existirá cuando se instale la versión FBM que lo contenga y se reinicie HA. No necesita cambios en el MCP genérico: su túnel ya puede llamar a los comandos WebSocket.

### Herramientas ya existentes
`fbm/competition/analysis` devuelve promedios, partidos de muestra, clasificaciones y anotadores. `fbm/competition/latest` recupera el calendario completo. `fbm/competition/team_roster` y `fbm/competition/team_player_stats` consultan plantillas y estadísticas con validación de pertenencia; las cuatro se han probado en la versión 0.2.2b19 (la última con una consulta acotada). Mantener todos los datos personales de menores fuera de sensores públicos. No interpretar `null` como cero. `automatic_refresh.status=pending` con `last_run=null` sigue pendiente de diagnóstico aparte.

### Criterios de liberación
Ejecutar pruebas de datos ausentes, marcadores inválidos, equipo fuera del grupo, orden cronológico y precedentes; comprobar registro WS, permisos de administrador y grupo seguido. Pasar CI de FBM y pruebas con HA Core real, luego prueba funcional en HA. No publicar beta ni instalar hasta completar validación. Antes de versión estable, actualizar README de `main` y notas de versión en inglés y español.
