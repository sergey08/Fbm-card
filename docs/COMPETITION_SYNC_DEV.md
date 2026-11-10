# Competition Sync — DEV architecture

## English

**Status: prototype, not released and not deployed to Home Assistant.** Stable FBM Card is 0.2.1.

### Data model

The primary unit is one verified `season_id + phase_id + group_id`. Following two teams in the same group must reuse a single local archive, never create parallel competition records. SQLite lives in `/config/fbm_competitions_<entry_id>.sqlite` and is initialized lazily, only through an explicit administrator command.

- `competitions`: verified identities and opt-in follow flags
- `snapshots`: timestamped normalized `standings`, `fixtures`, and per-opponent `roster` records
- Image URLs, image payloads and raw FBM DTO responses are not persisted.
- Snapshot timestamps use timezone-aware UTC; stale results cannot overwrite the most recent good observation.

### Current DEV commands (Home Assistant WebSocket, administrator only)

- `fbm/competition/sync`: `entry_id`, `equipo`, `desde`, `hasta`, `incluir_plantillas` (boolean)
- `fbm/competition/list`: `entry_id`
- `fbm/competition/latest`: `entry_id`, `season_id`, `phase_id`, `group_id`, `source` (`standings`, `fixtures`, `roster`), `subject` (team ID for roster, empty string otherwise)

Sync uses the already-validated official FBM guest identity, team-group identification, standings, schedule and roster APIs. It requests at most 20 distinct teams, sequentially, with a small inter-request delay. It does not trigger on integration startup, search or card render. Failure of one roster retains earlier valid snapshots; errors are summarized, never returned verbatim.

### Important blocker

The existing `async_team_group_identity()` confirms the phase and group, but currently sets `season_verified=False` even when a possible season identifier is present. **The DEV prototype intentionally returns `season_unverified` without writing data until the season identifier is verified against an authoritative FBM response.** Never mix different seasons using a guessed name such as 26/27.

### Next steps

1. Verify an official season identifier and exact group membership in an authenticated FBM response, without collecting private player photos.
2. Validate that the selected team standings include every competitor and that team schedule covers the group.
3. Test an explicit full-group synchronization in an isolated HA DEV environment.
4. Add a small HA summary entity per followed competition and authenticated MCP-facing query actions. WebSocket access alone is not a finished MCP connector.
5. Add controlled periodic refresh, incremental retention and statistics comparison only after load/privacy tests.

## Español

**Estado: prototipo, no publicado ni desplegado en Home Assistant.** La versión estable continúa siendo 0.2.1.

### Modelo de datos

La unidad de sincronización es `season_id + phase_id + group_id`, todos verificados. Si seguimos dos equipos del mismo grupo, comparten un único archivo de competición. SQLite se crea de forma diferida en `/config/fbm_competitions_<entry_id>.sqlite`, solo por orden explícita de un administrador.

- `competitions`: identidades verificadas y seguimiento voluntario
- `snapshots`: clasificación, calendario y plantilla normalizada de cada rival, con fecha de observación
- No se guardan fotografías, URLs de fotos ni respuestas FBM originales.
- Se conservan las instantáneas válidas anteriores cuando una petición falla.

### Comandos de desarrollo

Los comandos WebSocket `fbm/competition/sync`, `fbm/competition/list` y `fbm/competition/latest` requieren permisos de administrador. La sincronización usa la identidad invitada ya existente, limita la descarga a 20 equipos y consulta plantillas secuencialmente, sin solicitudes automáticas al iniciar HA.

### Bloqueo conocido

El método actual identifica oficialmente fase y grupo, pero **todavía no verifica la temporada**. Por eso este prototipo devuelve `season_unverified` y no guarda históricos hasta confirmar un identificador oficial de temporada. No debe deducirse usando el texto 26/27.

### Siguientes tareas

1. Confirmar temporada y miembros reales del grupo en la API.
2. Comprobar calendario y clasificación de todos los participantes.
3. Validar la sincronización completa en HA DEV.
4. Crear un sensor resumido por competición y consultas autenticadas para el MCP.
5. Incorporar actualización automática limitada e históricos comparables tras las pruebas.
