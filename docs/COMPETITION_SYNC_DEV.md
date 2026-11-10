# Competition Sync — DEV architecture

## English

**Status: prototype, not released and not deployed to Home Assistant.** Stable FBM Card is 0.2.1.

### Data model

The primary unit is one verified `season_id + phase_id + group_id`. Following two teams in the same group must reuse a single local archive, never create parallel competition records. SQLite lives in `/config/fbm_competitions_<entry_id>.sqlite` and is initialized lazily, only through an explicit administrator command.

- `competitions`: verified identities and opt-in follow flags
- `snapshots`: timestamped normalized `standings`, `fixtures`, and per-opponent `roster` records
- Image URLs, image payloads and raw FBM DTO responses are not persisted.
- Snapshot timestamps use timezone-aware UTC; stale results cannot overwrite the most recent good observation.

### Official season label from FBM search (simplified)

FBM's team search supplies the visible official season label (for example `26/27`), while the separate phase/group endpoint supplies the official phase and group identifiers without a distinct season ID. Following now uses the validated **official search label + official phase ID + official group ID**, after confirming the chosen team belongs to the group's standings. The label must have a consecutive `YY/YY` season format. It is stored as a **label**, not misrepresented as an undocumented numeric API season ID.

On refresh, the archive resolves the explicit prior selection using its official anchor team and phase/group IDs; it keeps the originally selected season label, rather than re-deriving it or fetching player records. Changed phase/group causes a safe stop. The two-player season-ID check remains an **optional administrator diagnostic** (`fbm/competition/verify_season`) for discrepancies and is never required for ordinary following or syncing. No player records are queried during selection or fixture-only refresh.

### Real Home Assistant 2026.11 API compatibility test

The separate CI workflow `.github/workflows/ha-real-api-smoke.yml` installs the **real Home Assistant Core 2026.11.0** package in a fresh Python 3.14 environment and runs `tests/ha_real_api_smoke.py`. It confirms that the FBM OptionsFlow factory, native menu, invalid-search form and complete search → verify → follow → refresh fixtures → unfollow with retained SQLite history operate with actual Home Assistant and Probatio classes, **without importing or starting the production server**. It is an integration-flow API compatibility check using fake FBM responses and temporary SQLite, not a frontend/browser validation, live season check or end-to-end HA server deployment. The normal offline unit/JS tests remain separate.

### Readable names in every competition menu

The confirmation, followed-group manager, manual refresh picker and unfollow confirmation now display official **team name, season label, phase name and group name** rather than the opaque FBM API identifiers. The SQLite archive preserves opaque identifiers as internal keys and stores the public short labels in separate columns with backward-compatible migrations. Existing beta archives are populated with names on their next successful refresh; until then the menu shows a generic competition number and season rather than the raw identifier. The existing Lovelace card bundle is unchanged.

### Native competition manager (DEV)

The integration's **Configure** button opens a native Home Assistant options flow. The selection now retains the **verified source-team identifier** in the competition row (`anchor_team_id`) to support future explicit refreshes of the group, without exposing it in the summary sensor. Existing DEV SQLite files are migrated in place, with historical snapshots preserved. No background jobs are started. The first implemented selection path is **Find team → Select team → Verify entire current competition → Confirm follow**. Searching uses the existing authenticated `async_search_teams` endpoint; the confirmation validates the official search season label, phase/group IDs and team membership in standings, without downloading any player details. If verification fails, nothing is followed or stored. The flow does not automatically download any rosters. **Manage → Select competition → Confirm unfollow** turns off following but preserves historical snapshots. It reuses the same SQLite archive as the WebSocket endpoints and summary sensor; duplicates are prevented by the season/phase/group composite key.

Direct **search by competition name without any team** is reserved for a later step because its official discovery endpoint has not yet been established; no fake competition lookup was added. UI labels are translated in English and Spanish. This is code-only DEV and has not been verified in Home Assistant.

### Concurrent stop-following and idempotent refresh (DEV)

A manual synchronization checks that the group is still followed before each roster request and again before writing snapshots. If a user stops following during a long request, it returns `not_followed`, does not request any additional player roster and does not persist the in-flight batch. Retrying an unchanged competition remains a successful operation with `records_written=0`; unchanged snapshots are deduplicated. This behavior is covered by synthetic offline tests, not live FBM deployment.

### Bounded individual match-statistics batches (DEV)

After an administrator explicitly requests roster download, the integration can fetch individual sporting statistics in **separate batches of at most five players per team** with at least 0.5 s between successful or failed requests. The admin-only WebSocket command `fbm/competition/player_stats_batch` accepts `entry_id`, `season_id`, `phase_id`, `group_id`, `equipo`, `offset`, `limit` (1–5). It reads player IDs from the already archived roster of the explicitly followed competition; it refuses unknown teams, unselected groups and unverified player-team response bindings. Responses return counts and `next_offset`, never player names or details.

SQLite stores only normalized `player_stats` snapshots keyed by player ID, with permitted per-match numeric sporting fields and global numbers exactly as provided by FBM. Missing global values remain `null`. Admin competition analysis can derive known player points from per-match scores and reports `partidos_con_puntos`; these are observed partial totals, not season totals if coverage is incomplete. The normal HA sensor remains **team-level only**. This feature is not in the installed b2 and is not yet a scheduled task.

### Manual refresh of a followed competition (DEV)

The **Configure → Refresh competition** options-flow path lists only explicitly followed groups with a retained verified `anchor_team_id`. It requires selecting the competition and **a separate confirmation** before making any FBM calls. The requested date window is bounded to 45 days in the past and 60 days in the future (105 days total). It refreshes official standings and group fixtures; **player-roster downloads are off by default** and require an explicit additional checkbox. `sync_group` enforces an `expected_competition` binding and aborts with `competition_changed` before fetching fixtures or rosters if the official season, phase or group has changed. An unfollowed group cannot be downloaded. There is no scheduler or automatic polling.

The isolated options-flow suite now exercises manual refresh, explicit roster consent, safe handling of missing anchors, and persistence of fixtures. These are simulations, not an in-production HA frontend validation.

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

The phase/group lookup does not return a separate season ID. The official season display label comes from FBM team search; persistent group selection uses that validated label plus phase and group IDs. Do not claim that it is a separate internal season ID.

### Native Home Assistant MCP-facing summary entity (DEV)

The sensor platform registers one entity per FBM config entry, named `FBM Competiciones`, with stable unique ID `fbm_<entry_id>_competitions`. Its numeric state is the count of followed and verified competition groups. The `groups` attribute lists at most 50 followed groups with the official season **label**, phase/group identifiers, counts and timestamps. Each group now also includes a bounded `ranking` (up to 20 teams, with positions and W/L where available) and `recent_results` (up to five completed fixtures with actual scores). These are public team-level sports data only: no player identities, rosters, photographs or venue addresses. The sensor reads local SQLite every five minutes; it does not call FBM or create a database on startup. The normal HA MCP entity-state tool can read this sensor after installation. Full player details stay out of attributes. For detailed results, the existing admin-only WebSocket command `fbm/competition/analysis` remains the authenticated read path, but must be tested through a suitable MCP/HA WebSocket bridge before claiming direct MCP functionality.

### Next steps

1. Validate the official FBM season search label and exact group membership in an authenticated DEV session, without collecting player photos.
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

### Temporada oficial visible de FBM (criterio simplificado)

La búsqueda de equipos de FBM proporciona la temporada oficial visible (por ejemplo, `26/27`) y la consulta del grupo proporciona los identificadores oficiales de fase y grupo, pero no otro identificador de temporada independiente. Para seguir una competición se emplea **etiqueta oficial de temporada + ID de fase + ID de grupo**, después de verificar que el equipo seleccionado figura en la clasificación. La etiqueta tiene que seguir el formato consecutivo `AA/AA`. No se presenta como un identificador numérico de API inexistente.

Al actualizar se reutiliza la selección voluntaria archivada, vinculada al equipo oficial de referencia y a la fase/grupo; no se buscan fichas de jugadores. Si cambian fase o grupo, se detiene con aviso. La comprobación cruzada de IDs de temporada de dos jugadores queda como **diagnóstico opcional para administradores** (`fbm/competition/verify_season`), no como requisito de cada actualización. El seguimiento inicial y la actualización sin plantillas no consultan datos de jugadores.

### Prueba de compatibilidad con Home Assistant 2026.11 real

El flujo CI independiente `.github/workflows/ha-real-api-smoke.yml` instala **Home Assistant Core 2026.11.0 real** en Python 3.14 y ejecuta `tests/ha_real_api_smoke.py`. Comprueba el registro de OptionsFlow, el menú, los formularios y el recorrido buscar → verificar → seguir → actualizar partidos → dejar de seguir conservando históricos, usando clases reales de Home Assistant y Probatio, **sin arrancar el servidor de producción**. Es una prueba funcional del flujo con API real de HA, FBM simulado y SQLite temporal, no una prueba visual del frontend ni una sincronización real de temporada. Se mantienen aparte las pruebas aisladas habituales.

### Nombres legibles en todos los menús de competiciones

La confirmación, la lista de competiciones seguidas, el selector de actualización y la confirmación para dejar de seguir muestran el **nombre del equipo, temporada, fase y grupo**, no los identificadores internos de FBM. SQLite conserva los identificadores como claves técnicas y guarda los nombres públicos por separado, migrando sin borrar los históricos. Las competiciones ya guardadas en la beta recibirán automáticamente los nombres en su próxima actualización correcta; mientras tanto se muestra un número de competición y la temporada, nunca el código interno. El JavaScript de las tarjetas existentes no se modifica.

### Gestor de competiciones nativo (DEV)

Desde **Configurar** de la integración FBM se abre un flujo de opciones de Home Assistant. Al seguir un grupo se conserva también el **identificador del equipo oficial usado como referencia** (`anchor_team_id`) para futuras actualizaciones controladas, sin exponerlo en el sensor resumen. Las bases SQLite DEV anteriores se migran sin eliminar históricos. Por ahora no hay tareas automáticas. La primera vía implementada es **Buscar equipo → Seleccionar equipo → Verificar competición completa → Confirmar seguimiento**. Usa la búsqueda ya validada de equipos; antes de seguir comprueba la etiqueta de temporada oficial obtenida de la búsqueda, la fase y el grupo y la pertenencia a la clasificación, sin descargar fichas de jugadores. Si falla la verificación no guarda datos ni activa seguimiento. Seleccionar una competición no descarga automáticamente las plantillas.

**Gestionar → Seleccionar competición → Confirmar dejar de seguir** detiene su seguimiento sin borrar históricos. El almacén compartido evita duplicados mediante temporada/fase/grupo. La búsqueda **directa por nombre de competición**, sin seleccionar equipo, queda pendiente de verificar su consulta real en la API FBM; no se ha inventado un servicio. Textos de la interfaz en español e inglés. Todo sigue en DEV, sin probarse todavía en Home Assistant.

### Cancelación durante la descarga y actualización sin cambios (DEV)

La sincronización manual comprueba que el grupo sigue seleccionado antes de consultar la plantilla de cada equipo y de nuevo antes de guardar instantáneas. Si se deja de seguir durante una descarga, devuelve `not_followed`, no consulta más plantillas ni guarda ese lote. Una actualización sin cambios se considera correcta, con `records_written=0`, y no crea duplicados. Comprobado con pruebas offline; falta validación funcional en HA.

### Lotes limitados de estadísticas individuales (DEV)

Tras descargar voluntariamente las plantillas, la integración puede recuperar estadísticas individuales en **lotes separados de hasta cinco jugadores por equipo**, con pausas de 0,5 s entre consultas. El nuevo WebSocket solo para administradores `fbm/competition/player_stats_batch` recibe `entry_id`, `season_id`, `phase_id`, `group_id`, `equipo`, `offset` y `limit` (1–5). Toma los jugadores de plantillas ya archivadas de competiciones seguidas; rechaza equipos desconocidos, grupos no seguidos y estadísticas sin asociación oficial jugador-equipo. Devuelve únicamente contadores y `next_offset`, no nombres ni detalles personales.

SQLite almacena instantáneas `player_stats` normalizadas por jugador, con puntos y otros valores deportivos por partido y datos globales exactamente como se publican. Los valores ausentes se conservan como `null`. El análisis administrativo calcula los puntos conocidos a partir de partidos individuales y muestra cuántos partidos tienen puntuación, sin presentarlos como totales completos de temporada cuando falta cobertura. El sensor normal de HA continúa siendo **solo de equipos**. No está aún en la beta b2 instalada y todavía no hay tarea automática.

### Actualización manual de una competición seguida (DEV)

En **Configurar → Actualizar competición** solo aparecen los grupos seguidos expresamente que conservan un `anchor_team_id` oficial. Tras seleccionar el grupo hace falta una **segunda confirmación** antes de consultar FBM. El período solicitado abarca 45 días anteriores y 60 posteriores (105 días). Actualiza clasificación y calendario de todo el grupo; la **descarga de plantillas está desactivada inicialmente** y requiere marcar una casilla adicional. `sync_group` exige que la identidad oficial coincida exactamente con la competición elegida: si cambia la temporada, fase o grupo, devuelve `competition_changed` antes de descargar partidos o jugadores. Un grupo no seguido no puede sincronizarse. Todavía no hay actualización automática.

Las pruebas aisladas cubren la actualización, el consentimiento específico para descargar plantillas, la ausencia segura de equipos de referencia y la persistencia de los partidos. No equivalen a una prueba visual en Home Assistant real.

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

La plataforma de sensores crea **una sola entidad por configuración FBM**, llamada `FBM Competiciones`, con ID único estable `fbm_<entry_id>_competitions`. Su estado es el número de grupos seguidos; el atributo `groups` contiene como máximo 50 competiciones seguidas con la **etiqueta** oficial de temporada, fase/grupo, contadores y fechas. Cada grupo incluye ahora también `ranking` (máximo 20 equipos, posiciones y victorias/derrotas disponibles) y `recent_results` (máximo cinco partidos finalizados con marcadores oficiales). Solo se muestran datos deportivos de equipos: no hay jugadores, plantillas, fotografías ni direcciones. Lee SQLite cada cinco minutos, sin consultar a FBM ni crear la base de datos al arrancar. El MCP de Home Assistant podrá consultar el estado como el de cualquier otro sensor **después de instalarlo**. No se exponen fotos, nombres ni estadísticas personales en sus atributos. El análisis detallado continúa en el comando WebSocket de administrador `fbm/competition/analysis`, que necesita validación con el puente MCP antes de afirmar acceso directo.

### Siguientes tareas

1. Confirmar temporada y miembros reales del grupo en la API.
2. Comprobar calendario y clasificación de todos los participantes.
3. Validar la sincronización completa en HA DEV.
4. Crear un sensor resumido por competición y consultas autenticadas para el MCP.
5. Incorporar actualización automática limitada e históricos comparables tras las pruebas.
