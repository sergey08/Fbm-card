# FBM Card 0.2.2b20 (Beta) — Archived match preview

## English

### New: read-only match scouting for HA-MCP
- Added administrator-only WebSocket command `fbm/competition/match_preview` for previously followed, locally archived FBM competitions.
- Returns next scheduled match, exact opponent, round, date and venue; each team's latest four completed games with numeric scores; previous head-to-head meetings; archive coverage and snapshot timestamps.
- No additional calls to FBM and no writes to SQLite. The command does not return player names, photographs or individual statistics.
- Rejects unfollowed competitions, unknown or ambiguous teams, invalid archive snapshots and missing results; missing values are not invented.
- Existing read-only commands `fbm/competition/analysis`, `fbm/competition/latest`, `fbm/competition/team_roster` and `fbm/competition/team_player_stats` remain unchanged and were verified using the HA-MCP connector against v0.2.2b19.
- Added isolated Python regression tests, authorization-path and WebSocket registration tests, HA Core 2026.11 smoke testing, and `docs/MCP_ARCHIVE_ACCESS.md`.

### Deployment and validation
This beta is **not installed or released by preparing this branch**. Install only after the full GitHub validation succeeds, the release is explicitly published, and a Home Assistant backup is confirmed. Then install **exactly v0.2.2b20** from HACS and restart Home Assistant. Test the new command with an administrator session, verify a non-administrator is denied, and confirm `sensor.competiciones` retains all followed groups. Roll back to `v0.2.2b19` if needed, preserving the existing SQLite data. No dashboard resource cache update should be necessary because the JavaScript cards are unchanged.

**Known limitation:** automatic group/player refresh health may still report `pending` with `last_run=null`; this beta does not change the scheduler. A passing offline/HA Core smoke test does not prove the new WebSocket command was tested in the user's live Home Assistant.

## Español

### Novedad: previa deportiva de solo lectura para HA-MCP
- Nuevo comando WebSocket `fbm/competition/match_preview`, exclusivo de administradores, para competiciones FBM seguidas y archivadas localmente.
- Devuelve el próximo partido, rival exacto, jornada, fecha y pabellón; los últimos cuatro encuentros con marcador de cada equipo; enfrentamientos anteriores; cobertura y fechas de los registros.
- No solicita nuevos datos a FBM ni escribe en SQLite. No devuelve nombres, fotografías ni estadísticas individuales de jugadores.
- Rechaza competiciones no seguidas, equipos desconocidos o ambiguos y archivos incompletos. No inventa resultados ni valores ausentes.
- Permanecen intactos los comandos existentes `fbm/competition/analysis`, `fbm/competition/latest`, `fbm/competition/team_roster` y `fbm/competition/team_player_stats`, comprobados mediante HA-MCP sobre la versión v0.2.2b19.
- Nuevas pruebas Python de regresión y autorización, comprobación del registro WebSocket, pruebas con HA Core 2026.11 y documentación `docs/MCP_ARCHIVE_ACCESS.md`.

### Instalación y validación
**Preparar esta rama no instala ni publica la beta.** Instalar solo después de superar toda la CI, publicar explícitamente la versión y confirmar una copia de seguridad de Home Assistant. Después seleccionar **exactamente v0.2.2b20** en HACS y reiniciar. Probar la consulta como administrador, comprobar rechazo de usuario no administrador y verificar que `sensor.competiciones` conserva todos los grupos seguidos. Si fuera necesario, volver a `v0.2.2b19` conservando SQLite. No hace falta cambiar el recurso Lovelace porque las tarjetas JavaScript no se modifican.

**Limitación conocida:** la sincronización automática de grupos/jugadores puede seguir mostrando `pending` y `last_run=null`; esta beta no modifica los temporizadores. Pasar las pruebas offline y HA Core no equivale a validar el nuevo comando WebSocket en la instalación real.
