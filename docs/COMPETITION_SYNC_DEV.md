# Competition Sync — DEV architecture

## English

**Status: prototype, not released and not deployed to Home Assistant.** Stable FBM Card is 0.2.1.

### Data model

The primary unit is one verified `season_id + phase_id + group_id`. Following two teams in the same group must reuse a single local archive, never create parallel competition records. SQLite lives in `/config/fbm_competitions_<entry_id>.sqlite` and is initialized lazily, only through an explicit administrator command.

- `competitions`: verified identities and opt-in follow flags
- `snapshots`: timestamped normalized `standings`, `fixtures`, and per-opponent `roster` records
- Image URLs, image payloads and raw FBM DTO responses are not persisted.
- Snapshot timestamps use timezone-aware UTC; stale results cannot overwrite the most recent good observation.

### Native competition manager (DEV)

The integration's **Configure** button opens a native Home Assistant options flow. The first implemented selection path is **Find team → Select team → Verify entire current competition → Confirm follow**. Searching uses the existing authenticated `async_search_teams` endpoint; the confirmation checks official phase/group, group standings membership and the same verified season across player details from two separate teams. If verification fails, nothing is followed or stored. The flow does not automatically download any rosters. **Manage → Select competition → Confirm unfollow** turns off following but preserves historical snapshots. It reuses the same SQLite archive as the WebSocket endpoints and summary sensor; duplicates are prevented by the season/phase/group composite key.

Direct **search by competition name without any team** is reserved for a later step because its official discovery endpoint has not yet been established; no fake competition lookup was added. UI labels are translated in English and Spanish. This is code-only DEV and has not been verified in Home Assistant.

### Explicit opt-in enforcement (DEV)

A group may be synchronized **only after it has been explicitly followed in the native competition manager**. A manual WebSocket `fbm/competition/sync` request for a verified but unselected group returns `status=not_followed` without calling the schedule or downloading players. The sync operation never calls `follow` itself. The follow step does not request rosters, and unfollow preserves already archived snapshots. The full search → select → verify → follow → manage → confirm unfollow flow is covered by offline integration-style tests using a temporary SQLite database and simulated Home Assistant flow APIs. **These tests do not yet constitute a visual test in a real HA deployment.**

### Current DEV commands (Home Assistant WebSocket, administrator only)

- `fbm/competition/verify_season`: `entry_id`, `equipo`. Explicit read-only metadata check: consults two players of distinct official group teams and returns only `season_match_verified` boolean, group status and team count; never player names, IDs or season IDs. Does not follow, persist or download all rosters.
- `fbm/competition/preview`: `entry_id`, `equipo`, `desde`, `hasta`. Fetches official group membership and fixtures without saving or requesting player rosters, even when season is unverified.
- `fbm/competition/sync`: `entry_id`, `equipo`, `desde`, `hasta`, `incluir_plantillas` (boolean)
- `fbm/competition/list`: `entry_id`
- `fbm/competition/analysis`: `entry_id`, `season_id`, `phase_id`, `group_id`. Offline comparison of every team in the group using archived standings, finished matches with valid scores, and official player total points where rosters exist. Returns safe missing-data markers, observation timestamps, and no images. This is a Home Assistant admin WebSocket command, **not yet a direct MCP tool**.
- `fbm/competition/latest`: `entry_id`, `season_id`, `phase_id`, `group_id`, `source` (`standings`, `fixtures`, `roster`), `subject` (team ID for roster, empty string otherwise)

Sync uses the already-validated official FBM guest identity, team-group identification, standings, schedule and roster APIs. It requests at most 20 distinct teams, sequentially, with a small inter-request delay. It does not trigger on integration startup, search or card render. Failure of one roster retains earlier valid snapshots; errors are summarized, never returned verbatim.

### Official season corroboration (new DEV code)

The official player detail DTO contains `idTemporadaActual` along with the exact player/team association. Before persistence, the sync now verifies that the selected team belongs to the official standings and checks matching `idTemporadaActual` values from one roster member of each of two distinct teams in that same group. If either detail cannot be verified or the season IDs conflict, the operation returns `season_unverified` without storing data. This is an implementation backed by already-tested DTO fields, **not yet tested live with two current group members**.

The archive now uses strict field allowlists for every source, excluding player photographs, team crests, image URLs, raw payload extras and unrecognized future fields.

### Important blocker

The phase/group lookup alone continues to return `season_verified=False`. The new two-team official detail verification may unblock storage; it still requires a real HA DEV validation. Never infer seasons from labels such as 26/27.

### Native Home Assistant MCP-facing summary entity (DEV)

The sensor platform registers one entity per FBM config entry, named `FBM Competiciones`, with stable unique ID `fbm_<entry_id>_competitions`. Its numeric state is the count of followed and verified competition groups. The `groups` attribute includes at most 50 triples `season_id`, `phase_id`, `group_id`, plus counts of teams/matches and observation timestamps. The sensor reads local SQLite every five minutes; it does not call FBM or create a database on startup. The normal HA MCP entity-state tool can read this sensor after installation. Full player details stay out of attributes. For detailed results, the existing admin-only WebSocket command `fbm/competition/analysis` remains the authenticated read path, but must be tested through a suitable MCP/HA WebSocket bridge before claiming direct MCP functionality.

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

### Gestor de competiciones nativo (DEV)

Desde **Configurar** de la integración FBM se abre un flujo de opciones de Home Assistant. La primera vía implementada es **Buscar equipo → Seleccionar equipo → Verificar competición completa → Confirmar seguimiento**. Usa la búsqueda ya validada de equipos; antes de seguir comprueba fase/grupo oficial, pertenencia a la clasificación y temporada concordante en dos fichas oficiales de jugadores de equipos distintos. Si falla la verificación no guarda datos ni activa seguimiento. Seleccionar una competición no descarga automáticamente las plantillas.

**Gestionar → Seleccionar competición → Confirmar dejar de seguir** detiene su seguimiento sin borrar históricos. El almacén compartido evita duplicados mediante temporada/fase/grupo. La búsqueda **directa por nombre de competición**, sin seleccionar equipo, queda pendiente de verificar su consulta real en la API FBM; no se ha inventado un servicio. Textos de la interfaz en español e inglés. Todo sigue en DEV, sin probarse todavía en Home Assistant.

### Seguimiento exclusivamente voluntario (DEV)

Una competición **solo puede sincronizarse después de haber sido seleccionada expresamente en el gestor de competiciones**. Una petición manual `fbm/competition/sync` dirigida a un grupo verificado pero no seleccionado devuelve `status=not_followed` sin descargar partidos ni plantillas. La sincronización nunca añade automáticamente competiciones al seguimiento. Seleccionar un grupo no descarga plantillas y dejar de seguirlo conserva los históricos. El flujo completo buscar → seleccionar → verificar → seguir → gestionar → confirmar baja se prueba sin red con un archivo SQLite temporal y simulaciones de Home Assistant. **Estas pruebas todavía no equivalen a una validación visual sobre HA real.**

### Comandos de desarrollo

El comando `fbm/competition/verify_season` permite comprobar sin escrituras si las temporadas oficiales de las fichas verificadas de dos equipos distintos coinciden. Devuelve únicamente una confirmación, el estado y el número de equipos; nunca identificadores de jugadores ni de temporada. Las comprobaciones individuales de estadísticas de Pinto Basket y Parla Basket en la versión estable han devuelto `complete`, pero eso **no confirma por sí mismo** que la temporada de ambos sea idéntica. La nueva comprobación requiere validación real tras instalar DEV.

Los comandos WebSocket `fbm/competition/preview`, `fbm/competition/sync`, `fbm/competition/list`, `fbm/competition/latest` y `fbm/competition/analysis` requieren permisos de administrador. `analysis` compara todos los equipos del grupo usando la clasificación y los partidos finalizados con marcador disponible, y ordena anotadores solo cuando FBM publica sus puntos totales. Trabaja exclusivamente sobre los datos archivados y devuelve fechas de observación. **Todavía no es una herramienta MCP directa.** La vista previa consulta equipos y calendario del grupo sin persistencia ni descargas de plantillas, incluso cuando la temporada no esté verificada. La sincronización usa la identidad invitada ya existente, limita la descarga a 20 equipos y consulta plantillas secuencialmente, sin solicitudes automáticas al iniciar HA.

### Verificación cruzada de temporada (nuevo código DEV)

Las fichas oficiales de jugador incluyen `idTemporadaActual` y la vinculación explícita jugador-equipo. Antes de guardar datos, la sincronización verifica que el equipo seleccionado pertenece a la clasificación y comprueba que un jugador de cada uno de dos equipos distintos del grupo tiene el mismo identificador de temporada, con asociaciones oficiales verificadas. Si faltan datos o hay discrepancias, se devuelve `season_unverified` y no se almacena nada. **Falta validar la comprobación con miembros reales del grupo en HA DEV.**

El archivo SQLite utiliza listas blancas de campos deportivos para clasificación, partidos y jugadores; excluye fotos, escudos, URLs de imágenes y campos adicionales desconocidos.

### Bloqueo conocido

La consulta de fase/grupo por sí sola continúa sin verificar la temporada. La nueva comprobación de dos equipos podría permitir la sincronización, pero **todavía falta demostrarlo con datos reales en Home Assistant DEV**. No debe inferirse la temporada por una etiqueta como 26/27.

### Sensor nativo de Home Assistant para el MCP (DEV)

La plataforma de sensores crea **una sola entidad por configuración FBM**, llamada `FBM Competiciones`, con ID único estable `fbm_<entry_id>_competitions`. Su estado es el número de grupos seguidos; el atributo `groups` contiene como máximo 50 grupos con IDs oficiales de temporada/fase/grupo, cantidades de equipos/partidos y fechas de consulta. Lee SQLite cada cinco minutos, sin consultar a FBM ni crear la base de datos al arrancar. El MCP de Home Assistant podrá consultar el estado como el de cualquier otro sensor **después de instalarlo**. No se exponen fotos, nombres ni estadísticas personales en sus atributos. El análisis detallado continúa en el comando WebSocket de administrador `fbm/competition/analysis`, que necesita validación con el puente MCP antes de afirmar acceso directo.

### Siguientes tareas

1. Confirmar temporada y miembros reales del grupo en la API.
2. Comprobar calendario y clasificación de todos los participantes.
3. Validar la sincronización completa en HA DEV.
4. Crear un sensor resumido por competición y consultas autenticadas para el MCP.
5. Incorporar actualización automática limitada e históricos comparables tras las pruebas.
