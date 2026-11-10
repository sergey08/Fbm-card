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

- `fbm/competition/preview`: `entry_id`, `equipo`, `desde`, `hasta`. Fetches official group membership and fixtures without saving or requesting player rosters, even when season is unverified.
- `fbm/competition/sync`: `entry_id`, `equipo`, `desde`, `hasta`, `incluir_plantillas` (boolean)
- `fbm/competition/list`: `entry_id`
- `fbm/competition/latest`: `entry_id`, `season_id`, `phase_id`, `group_id`, `source` (`standings`, `fixtures`, `roster`), `subject` (team ID for roster, empty string otherwise)

Sync uses the already-validated official FBM guest identity, team-group identification, standings, schedule and roster APIs. It requests at most 20 distinct teams, sequentially, with a small inter-request delay. It does not trigger on integration startup, search or card render. Failure of one roster retains earlier valid snapshots; errors are summarized, never returned verbatim.

### Official season corroboration (new DEV code)

The official player detail DTO contains `idTemporadaActual` along with the exact player/team association. Before persistence, the sync now verifies that the selected team belongs to the official standings and checks matching `idTemporadaActual` values from one roster member of each of two distinct teams in that same group. If either detail cannot be verified or the season IDs conflict, the operation returns `season_unverified` without storing data. This is an implementation backed by already-tested DTO fields, **not yet tested live with two current group members**.

The archive now uses strict field allowlists for every source, excluding player photographs, team crests, image URLs, raw payload extras and unrecognized future fields.

### Important blocker

The phase/group lookup alone continues to return `season_verified=False`. The new two-team official detail verification may unblock storage; it still requires a real HA DEV validation. Never infer seasons from labels such as 26/27.

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

Los comandos WebSocket `fbm/competition/preview`, `fbm/competition/sync`, `fbm/competition/list` y `fbm/competition/latest` requieren permisos de administrador. La vista previa consulta equipos y calendario del grupo sin persistencia ni descargas de plantillas, incluso cuando la temporada no esté verificada. La sincronización usa la identidad invitada ya existente, limita la descarga a 20 equipos y consulta plantillas secuencialmente, sin solicitudes automáticas al iniciar HA.

### Verificación cruzada de temporada (nuevo código DEV)

Las fichas oficiales de jugador incluyen `idTemporadaActual` y la vinculación explícita jugador-equipo. Antes de guardar datos, la sincronización verifica que el equipo seleccionado pertenece a la clasificación y comprueba que un jugador de cada uno de dos equipos distintos del grupo tiene el mismo identificador de temporada, con asociaciones oficiales verificadas. Si faltan datos o hay discrepancias, se devuelve `season_unverified` y no se almacena nada. **Falta validar la comprobación con miembros reales del grupo en HA DEV.**

El archivo SQLite utiliza listas blancas de campos deportivos para clasificación, partidos y jugadores; excluye fotos, escudos, URLs de imágenes y campos adicionales desconocidos.

### Bloqueo conocido

La consulta de fase/grupo por sí sola continúa sin verificar la temporada. La nueva comprobación de dos equipos podría permitir la sincronización, pero **todavía falta demostrarlo con datos reales en Home Assistant DEV**. No debe inferirse la temporada por una etiqueta como 26/27.

### Siguientes tareas

1. Confirmar temporada y miembros reales del grupo en la API.
2. Comprobar calendario y clasificación de todos los participantes.
3. Validar la sincronización completa en HA DEV.
4. Crear un sensor resumido por competición y consultas autenticadas para el MCP.
5. Incorporar actualización automática limitada e históricos comparables tras las pruebas.
