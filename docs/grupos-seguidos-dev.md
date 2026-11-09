# Grupos seguidos — estado de desarrollo (DEV, 09/11/2026)

## Implementado
- `custom_components/fbm/followed_groups_store.py`: SQLite independiente para seguimiento explícito por clave (temporada, grupo), snapshots de clasificación, fecha UTC y preservación histórica después de dejar de seguir.
- `tests/test_followed_groups_store.py`: 4 pruebas (seguimiento opt-in, conservación al dejar de seguir, aislamiento y persistencia, rechazo de datos anteriores/fuentes no verificadas).
- CI para commit `487686dadf0c0ddb2dbed7773f42685718f58768`: dos workflows terminados en **success**. Esto valida el código/CI, **no** la sincronización real en Home Assistant.
- Las búsquedas de equipo y sus preferencias siguen intactas. No se ha tocado la identidad FBM, `main`, ni la configuración actual de tarjetas.

## No implementado ni validado
- Almacenamiento aún **NO integrado** en `__init__.py`, coordinador, sensores ni WebSocket. No se ha desplegado en HA, ni siquiera en DEV.
- El identificador de temporada necesita verificación real; no migrar datos con claves supuestas.
- Política de intervalos laborables/fin de semana, opciones de integración y actualización manual, resumen de salud por grupo y fuente; todos pendientes.
- Calendario de grupo: consulta fallida; jugadores/estadísticas: campos presentes en APK pero respuestas/cobertura aún no validadas; **no almacenar ni presentar como funcional**.
- Recuperación automática de sesión tras reinicio con identidad guardada: sin prueba extremo a extremo nueva.
- La búsqueda en tiempo real nunca debe crear seguimientos ni sensores; si usa caché, mostrar fecha/antigüedad.

## Capacidades MCP verificadas
El conector Home Assistant ofrece `ha_get_state` para estado y atributos de entidades, `ha_get_history` para historial del recorder y `ha_list_services`/`ha_call_service` para acciones registradas. Consulta real a `ha_list_services(domain="fbm")` devolvió **0 servicios**. No se ha identificado comando MCP que ejecute directamente `fbm/group/... ` por WebSocket ni API detallada SQLite. Una entidad resumen con fecha/estado podrá consultarse cuando exista; para partidos y jugadores detallados se necesita una interfaz adicional cuya exposición al conector se compruebe realmente.

## Próximas tareas en orden
1. Probar recuperación de sesión existente y verificar IDs oficiales de temporada/grupo.
2. Integrar el almacén en un coordinador opt-in (sin trabajos programados antes de selección), opciones de intervalos y errores aislados por fuente.
3. Crear sensores de resumen con `last_success`, `last_attempt`, `stale`, `status` y `source_status`; acción manual; sin datos personales innecesarios en atributos.
4. Solucionar calendario con respuesta oficial observada, antes de activar ingesta. Validar disponibilidad/privacidad de jugadores por categoría.
5. Tarjetas lectoras del almacén y favoritos solo visuales; mantener búsqueda en tiempo real separada. Probar extremo a extremo con HA DEV.

No dar por desplegado ni operativo nada de los puntos pendientes.

## 09/11/2026 — Consulta oficial previa al seguimiento
- Nuevo método `AficionFBMAdapter.team_group_identity(team_id)`: solicita una sola vez `fasesGrupos` al backend oficial de Afición FBM y reutiliza `current_phase_group`/`classification_selection` para comprobar pertenencia al grupo actual y tipo de fase. Devuelve identificadores oficiales de equipo, fase y grupo, y nombres, **sin datos de sesión**.
- Se expone como `fbm/team/group_identity` en WebSocket para administradores, con `entry_id` y `equipo`. Es exclusivamente de lectura: no sigue grupos, no crea sensores ni modifica tarjetas. Este método no usa caché, para evitar antigüedad oculta.
- `season_id: null` y `season_verified: false` son intencionados: la respuesta de fases comprobada no acredita la identidad de temporada. El texto de temporada en resultados de búsqueda no puede convertirse en un ID oficial por suposición.
- Se añadieron pruebas del origen de los IDs, de permisos de administrador, validación del equipo y ausencia de caché silenciosa. La API real de Home Assistant y la sesión FBM siguen sin prueba E2E con este nuevo comando.
- **Puerta de seguridad:** el coordinador de grupos y su SQLite permanecen aislados; sin ID oficial de temporada validado no debe habilitarse el seguimiento persistente en HA ni una sincronización programada. No modificar el esquema de grupos para adoptar el nombre de temporada como ID.


## 09/11/2026 — Puente oficial de sincronización con bloqueo por temporada
- Añadido `verified_group_fetcher.py` con `VerifiedGroupFetcher(client, representative_teams)`. El adaptador exige un equipo representante elegido explícitamente para el par (temporada, grupo), consulta el grupo oficial actual por `async_team_group_identity` y verifica coincidencia exacta del equipo, grupo, temporada y marca `season_verified=True` **antes** de pedir clasificación. El servidor y la sesión deben seguir validados por el cliente FBM ya existente; el campo `source` no autentica por sí solo el origen.
- El contrato observado actualmente devuelve `season_id=None, season_verified=False`, por lo que **el puente se bloquea intencionadamente** y no consulta clasificación ni escribe SQLite. Esto evita mezclar temporadas durante la transición al seguimiento persistente.
- Cinco tests aislados cubren temporada no verificada, ausencia de representante, identidad de temporada/grupo incompatible, vínculo hipotético verificado y rechazo de fuente distinta. Los tests usan respuestas sintéticas; el caso de temporada verificada **no** demuestra que FBM lo devuelva realmente.
- Todavía no se ha conectado el puente al coordinador HA, no hay CRUD de grupos ni sensores, temporizador o acciones manuales de Home Assistant. No se modifica `main`, configuración de equipos ni identidad guardada, ni se instala nada.
- Investigación pendiente prioritaria: obtener, con la sesión legítima existente, respuesta real de un endpoint FBM que contenga un ID de temporada y documentar su relación con `id_grupo`/equipo. Hasta entonces, la barrera de validación debe permanecer activa.


## Diagnóstico seguro de temporada, 09/11/2026
- Nuevo módulo `season_evidence.py` inspecciona exclusivamente los campos candidatos `IdTemporada`, `idTemporada`, `id_temporada`, `idTemporadaActual`, `IdTemporadaActual` en tres niveles precisos de la respuesta oficial `fasesGrupos`: raíz, fase actual y grupo actual. Devuelve solo candidato, nombre de campo y origen; no exporta el JSON bruto, UID, `key` o `id_dispositivo`.
- `AficionFBMAdapter.team_group_identity()` incorpora `season_candidates`, `season_evidence_status` (`none`, `unverified`, `conflicting`) y mantiene **SIEMPRE** `season_verified=False`, `season_id=None`. Encontrar un campo con nombre de temporada es una pista, no prueba de vínculo estable ni autorización de sincronización.
- Seis tests sintéticos verifican ausencia de candidatos, presencia en lista blanca, conflictos, exclusión de otras fases/grupos, rechazo de ambigüedades, filtrado de tipos y protección de campos privados.
- Para validar en HA hay que instalar controladamente este backend DEV y ejecutar el comando administrador de solo lectura `fbm/team/group_identity` con el ID de equipo oficial ya configurado y sesión vigente. No se debe volcar la respuesta entera ni registrar credenciales. **El conector MCP de HA disponible no proporciona una llamada WebSocket arbitraria**, por lo que esta prueba real no se ha ejecutado aquí.
- Sin resultado real no se desbloquea el identificador ni se activa SQLite, jobs o sensores. La web pública FBM TV dispone de selector de temporada, pero no se ha demostrado que sus IDs sean intercambiables con los de Afición FBM: no fusionar catálogos ni fabricar asociación.


## 09/11/2026 — APK 5.0.42 reanalizada a partir del ZIP aportado

Archivo local: `Afición FBM-5.0.42-split-apks(1).zip`, contiene `base.apk` con `classes2.dex` (no se incorpora el APK al repositorio). Se analizaron tablas DEX de cadenas, métodos y sus cuerpos, buscando instrucciones Dalvik `const-string` asociadas a acciones. Este análisis no extrae tokens ni realiza llamadas autenticadas.

**Calendario:**
- `Lx5/k;->f` incluye literalmente `horariosJornadas`, `id_dispositivo`, `key`, `id_equipo`, `id_fase`, `id_grupo`, `id_ronda`, `fecha_inicial`, `fecha_final`.
- `Lk5/m;->k` contiene `horariosJornadas` y los mismos identificadores de fase/grupo/ronda/fechas, pero **`id_categoria_competicion`** en lugar de `id_equipo`. Son rutas distintas de contexto equipo y categoría.
- También existen las variantes `horariosFecha` en `Lx5/k;->e` y `Lk5/m;->j`. No se asume todavía igualdad de respuesta ni se activan métodos alternativos de red.
- Corregido `team_phases.schedule_selection`: se puede solicitar el grupo actual aunque FBM incluya una lista de rondas disponibles. Solo una elección explícita de ronda usa `id_ronda` y deja vacío `id_grupo`. Antes, el mero hecho de que existiesen rondas bloqueaba una consulta de grupo. Es una corrección estructural basada en los parámetros observados, **no una prueba real de calendario funcional**. Prueba actualizada en `tests/test_team_protocol.py`.

**Jugadores:**
- `LH5/j;->g` presenta acción `jugadores` con `id_equipo`; `LH5/j;->e` presenta `detalleJugador` con `id_jugador`; `LH5/j;->f` presenta `buscarJugador` con `nombre`, `texto`, `skip`. En los métodos también aparecen `accion`, `id_dispositivo`, `key`, `application/x-www-form-urlencoded`.
- Añadido `player_protocol.py` para crear los dos primeros formularios según esos campos literales y pruebas aisladas. **No efectúa solicitudes de red**: la asociación de cada acción con el endpoint efectivo y el DTO de respuesta siguen sin demostración completa. No hay jugadores ni estadísticas activados en tarjeta o integración.

**Estadísticas:** `LK4/d;->invokeSuspend` contiene `estadisticaPartido` próximo a lógica de datos deportivos, pero la acción, campos y URL efectivos no están aún reconstruidos. No asumir que sea consulta pública ni que cubra categorías de menores.

**Arquitectura:** cuando se verifique cada consulta con respuesta FBM auténtica, el mismo adaptador alimentará tanto tarjetas bajo demanda como sincronización opt-in. El buscador no sigue grupos ni crea entidades. No se instaló código ni se modificaron identidad, equipos o `main`.


## 09/11/2026 — Auditoría de métodos de la APK y diagnóstico de calendario
- Se ha inspeccionado otra vez el ZIP Afición FBM 5.0.42 entregado por el usuario, abriendo `base.apk/classes2.dex` y resolviendo `method_ids` y las instrucciones `invoke-*` de los cuerpos de método. **Verificado en el bytecode**, no solo por cadenas próximas: `Lx5/k;->f` y `Lk5/m;->k` crean `HttpRequestBuilder`, establecen `HttpMethod.POST`, pasan URL mediante `HttpRequestKt.url`, asignan `Content-Type: application/x-www-form-urlencoded`, concatenan pares con `StringValuesBuilder.append`, construyen `FormDataContent` y ejecutan `HttpStatement.execute`.
- `Lx5/k;->f` contiene acción `horariosJornadas` con `id_equipo`; `Lk5/m;->k` contiene la misma acción pero `id_categoria_competicion`. Distinción de rutas probada en código; **aún no está confirmada la URL final ni la semántica exacta de la respuesta en cada modalidad**.
- Los métodos `LH5/j;->g`, `e`, `f` hacen POST form-urlencoded para `jugadores`, `detalleJugador`, `buscarJugador` respectivamente. No se ha probado el resultado real ni cobertura por categoría.
- Nueva `schedule_probe.py`: solo reconoce nombres de campos permitidos (`partidos`, `jornadas`, `listaJornadas`, etc.), número de entradas y campos conocidos del primer elemento. No devuelve respuestas completas, contenido deportivo personal ni mensaje de error bruto.
- Refactor del adaptador `AficionFBMAdapter._team_schedule_response()`: **un único flujo oficial** de fases -> horarios, compartido entre `team_schedule()` (normalizado para tarjeta) y `team_schedule_probe()` (solo estructura). El cliente ofrece `async_team_schedule_probe()` sin caché; nuevo WebSocket administrador `fbm/team/schedule_probe` con `entry_id`, `equipo`, `desde` y `hasta`. No ejecuta tráfico salvo petición explícita del administrador.
- `tests/test_schedule_probe.py` cubre esquema clásico, jornadas anidadas, supresión de mensajes de error/secretos y respuestas no objeto. Tests de carga y registro WebSocket actualizados.
- **Pendiente**: instalar y validar backend DEV con la sesión existente para consultar el diagnóstico real; el MCP de HA disponible no ha demostrado envío de comandos WS arbitrarios. No se ha desplegado, registrado dispositivo ni modificado tarjetas, configuración de equipos, `main` o almacenamiento.


## 09/11/2026 — Hallazgo en DTOs reales: nombres camelCase
Se analizó directamente el ZIP APK aportado de nuevo, leyendo las tablas `type_ids` y `field_ids` de `classes2.dex`, y relacionando las clases de respuesta con los métodos de petición identificados:
- `Lx5/k;->f` y `->e` esperan `com.indalweb.appaficion.detalle_equipo.data.dto.EquipoPartidoResponseDto`, con `partidos: List`, `jornadaActual: Int`, `error: String`. Los elementos `EquipoPartidoDto` incluyen **`idPartido`, `nombreEquipoLocal`, `nombreEquipoVisitante`, `numeroJornada`, `fecha`, `hora`, `estado`, `resultados`, `campoJuego`, `direccionCampo`, `fechaHoraUTC`**. `ResultadosDto` contiene `resultadoLocal`, `resultadoVisitante`, `resultadosPeriodo`.
- El normalizador DEV anterior solo buscaba `IdPartido`, `NombreEquipoLocal`, `Resultados` y similares (PascalCase). **Corregido** `team_schedule.normalize_team_schedule` para admitir el modelo camelCase de la APK y preservar temporalmente los datos experimentales PascalCase; selección estricta de una variante por registro, sin mezclar ni fabricar resultados en estados desconocidos.
- El modo categoría usa un DTO diferente, `PartidosCategoriaResponseDto`: incluye `partidos`, pero **no** `jornadaActual`, así que no debe ser procesado ciegamente por el normalizador de calendario de equipo. Su futuro adaptador necesita normalización separada tras comprobar elementos y respuesta reales.
- La respuesta `JugadoresEquipoResponseDto` usa `misJugadores: List`; sus elementos `JugadorEquipoDto` incluyen `id`, `nombre`, `nombreEquipo`, `temporada`, `partidosJugados`, `puntosTotales`, `mediaPuntos`, etc. `JugadorDetalleResponseDto` contiene `jugador`, `idTemporadaActual`, `equiposJugador`; el código de estadísticas aún no está habilitado.
- Los nombres provienen de campos de clases Kotlin serializables del APK; **todavía hay que confirmar los nombres JSON efectivos** (posibles anotaciones de serialización) y las respuestas auténticas. Este hallazgo identifica una causa probable de error de visualización, **no demuestra una descarga real exitosa**.
- Actualizado también `schedule_probe.py` para incluir los campos camelCase de la APK en su inventario anonimizado. Añadidas pruebas aisladas de normalización y privacidad. El motor de petición sigue siendo compartido; la sincronización opt-in y frontend no se modificaron.


## 09/11/2026 — Normalizadores reutilizables: categoría, plantilla y estadísticas

- Se reexaminó directamente el archivo APK recibido y se contrastaron los `field_ids` de los DTO Kotlin de `classes2.dex`. **No se ha ejecutado una petición HTTP real nueva**, ni se han extraído datos de menores.
- `PartidosCategoriaResponseDto` contiene `partidos` pero no `jornadaActual`, a diferencia de `EquipoPartidoResponseDto`. Refactor de `team_schedule.py`: `_normalize_matches()` es el normalizador único de partidos y sus marcadores; `normalize_team_schedule()` exige jornada de equipo y `normalize_category_schedule()` acepta respuesta de categoría dejando `jornada_actual=None`, sin inventar un número. Pruebas aisladas de ambos tipos de respuesta.
- `JugadoresEquipoResponseDto` contiene `misJugadores` y `JugadorEquipoDto` utiliza nombres `id`, `nombre`, `nombreEquipo`, `temporada`, `partidosJugados`, `puntosTotales`, `mediaPuntos`, `puntosPorPartido`, `minutosPorPartido`. Añadido `team_roster.py` que mapea solo datos deportivos permitidos, valida IDs, descarta fotos/datos extra y **no inventa ceros cuando no hay estadísticas**. Sigue sin conectarse al backend hasta validar respuesta real.
- `EstadisticasJugadorEquipoPartidoDto` contiene `puntos`, `faltascometidas`, `faltasrecibidas`, `rebotes`, `asistencias`, `recuperaciones`, `perdidas`, `valoracion` y otros. Añadido `match_player_stats.py` como normalizador de **un registro** de jugador/partido; no supone estructura de listas ni ruta completa del endpoint. Sin cobertura de partidos/estadísticas reales comprobada todavía.
- Pruebas adicionales `test_team_roster.py`, `test_match_player_stats.py` y casos nuevos en `test_team_schedule.py` verifican rechazo de entradas inválidas, campos opcionales y ausencia de filtraciones de elementos ajenos. Todos usan respuestas sintéticas y no demuestran cobertura real por categoría.
- **Arquitectura:** normalizadores puros reutilizables por consultas directas y futuros grupos sincronizados; no bifurcar motores de descarga. La activación de jugadores y estadísticas, y la categoría por red, siguen bloqueadas hasta verificar endpoint, esquema JSON real y disponibilidad/privacidad en categorías infantiles. No se desplegó ni se tocó `main`, identidad, favoritos o tarjetas.


## 09/11/2026 — Plantillas reales: trazado exacto de endpoint y conexión bajo demanda

- Reinspeccionado binario `Afición FBM-5.0.42-split-apks(1).zip` → `base.apk/classes2.dex` siguiendo instrucciones Dalvik `iget-object`, `HttpRequestKt.url`, `HttpMethod.POST`, además de asignaciones de campos URL en inicializadores. **Contrato verificado por bytecode:** `LH5/j;->g` lee `LH5/j;->d` → `https://appaficionfbm.gesdeportiva.es/v2/equipo.ashx` para `accion=jugadores`, `id_equipo`. `LH5/j;->e` lee `LH5/j;->b` → `/v2/jugador.ashx` para `detalleJugador`. Se utiliza sesión técnica existente; no registrar ni fabricar UID.
- En DEV se habilitó **únicamente** consulta explícita de plantilla por equipo: `player_protocol.players_fields` → transporte oficial `post_team_form` (allowlist nueva acción `jugadores`) → `AficionFBMAdapter.team_roster` → `normalize_team_roster` de `misJugadores` → `IndependentClient.async_team_roster` con caché de 120 segundos → WS admin `fbm/team/players`. Ramas y directos comparten el mismo adaptador; no hay programación ni seguimiento por esta consulta.
- `fbm-card.js` y `custom_components/fbm/www/fbm-card.js` sincronizados en dev: pestaña Jugadores ofrece botón **Consultar jugadores FBM**; solo presenta nombres y datos deportivos opcionales autorizados (PJ, puntos, media) de la respuesta normalizada. Se guarda únicamente en memoria de la tarjeta, asociado a equipo e ID de integración, sin `localStorage`, sin petición automática, sin fotos ni PII adicionales. Los resultados de tarjetas fijas independientes permanecen separados.
- Nuevas pruebas Python: acción y endpoint POST, adaptador y normalización, WebSocket con permisos de administrador. Nuevas pruebas Node: consulta explícita/no automática, independencia de tarjetas y rechazo de respuesta no válida. Último commit verificado en GitHub Actions `9d34d202`, dos workflows SUCCESS (42712118910 / 42712128339).
- **No se ha probado todavía el resultado real de `accion=jugadores` con sesión FBM viva en HA**; el comando no existe en la versión actualmente instalada. Un resultado vacío o error no debe generar jugadores ficticios. No se ha conectado todavía la consulta de detalle de jugador ni de estadísticas de partido; faltan verificar sus contratos y cobertura por categoría. No hay sincronización operativa de jugadores ni calendario.
- `main`, Home Assistant instalado, identidad, favoritos y equipos Gael/Zoe inalterados. No hubo reinicio, despliegue ni nueva identidad.


## 09/11/2026 — Fichas de jugadores desde APK oficial (DEV)

- Se volvió a revisar el APK Afición FBM 5.0.42 aportado. El método `LH5/j;->e` utiliza POST `application/x-www-form-urlencoded` con `accion=detalleJugador`, `id_jugador`, `id_dispositivo` y `key` hacia `https://appaficionfbm.gesdeportiva.es/v2/jugador.ashx`. `JugadorDetalleResponseDto` expone `jugador` (`DetalleJugadorDto`), `equiposJugador` y `idTemporadaActual`; no se asume que otros endpoints o categorías tengan datos ampliados.
- Nuevo `player_detail.py`: transporte limitado al único formulario aprobado y normalización conservadora de `jugador`; requiere coincidencia exacta con el ID solicitado y conserva únicamente nombre e indicadores deportivos públicos, sin fecha de nacimiento, fotos, clave ni respuesta bruta.
- Integrado en `AficionFBMAdapter.player_detail`, `IndependentClient.async_player_detail` (caché 120 s) y comando administrador `fbm/player/detail` en WebSocket. No se crea identidad ni seguimiento; usa la sesión vigente.
- Tarjetas `fbm-card.js` y su copia empaquetada sincronizadas: en la lista obtenida con `Consultar jugadores FBM`, cada fila permite **Ver ficha** mediante pulsación explícita. Se conserva el detalle solo en memoria y vinculado a jugador, equipo y entrada FBM. Una respuesta tardía después de cambiar de equipo se descarta. Nunca se solicita la ficha automáticamente.
- Tests Python de transporte, endpoint, validación del ID, campos confidenciales, WebSocket admin y registros; tests Node de independencia y rechazo de respuesta cruzada por cambio de equipo. CI sobre código simulado, no pruebas reales del servidor.
- **Pendiente imprescindible:** desplegar juntos backend y frontend DEV de forma controlada y comprobar respuesta real del backend FBM con la identidad ya existente; ninguna funcionalidad nueva de jugadores se ha validado visualmente en HA. No se ha realizado despliegue, reinicio ni registro. No se han conectado estadísticas por partido `JugadorDatosPartidoDto` porque falta validar su solicitud y disponibilidad, especialmente en categorías de menores.
- `main`, identidad persistida, favoritos y tarjetas actuales de Gael/Zoe sin alteración. El sincronizador opt-in sigue aislado; ambas modalidades utilizarán el mismo motor de descarga una vez validadas.


## 09/11/2026 — Contrato de estadísticas de jugador encontrado en APK

Se examinó directamente el APK facilitado, `classes2.dex`, resolviendo métodos `LH5/j;->c` y `LH5/j;->d`, sus literales `const-string` y campos de instancia usados como URL en `HttpRequestKt.url`:
- Ambos métodos leen `LH5/j;->b` → **`/v2/jugador.ashx`** y realizan POST form-urlencoded con `id_dispositivo`, `key` más **cuatro identificadores deportivos obligatorios**: `id_jugador`, `id_equipo`, `id_componente_club`, `id_temporada`.
- `LH5/j;->c`: `accion=datosGlobalesJugadorEquipo`, modelo `JugadorDatosGlobalesResponseDto`. Contiene, entre otros, `puntosTotalesJugador`, `puntosMediaJugador`, `faltasCometidasTotalesJugador`, rebotes y asistencias; `mostrarDatosEstadisticosAmpliados` informa de cobertura ampliada.
- `LH5/j;->d`: `accion=datosMediasJugadorPartidos`, modelo `DatosMediasJugadorPartidosResponseDto` con lista **`listaDatosPartido`**. El DTO `JugadorDatosPartidoDto` contiene `idPartido`, `puntos`, `faltaCometida`, `faltaRecibida`, `rebotesTotal`, `asistencia`, `valoracion`, fechas y rival; varias estadísticas se modelan como **String** en la APK, no como enteros.
- Los identificadores adicionales no deben deducirse del nombre de categoría, año o ID de jugador. Aunque el DTO `JugadorDetalleResponseDto` tiene `idComponenteClub` e `idTemporadaActual`, **hay que comprobar en una respuesta oficial auténtica** su vinculación exacta a cada jugador/equipo antes de permitir descarga. Nunca usarlos para alterar el seguimiento de grupos.
- Incorporados `player_protocol.player_stats_fields()` para construir únicamente las dos acciones permitidas y `player_statistics.py` para normalizar estadísticas globales y lista de partidos, preservando campos ausentes como `None`, convirtiendo solo números verificables y filtrando información adicional. Pruebas sintéticas y sin red en `tests/test_player_statistics.py`.
- **No hay todavía llamadas a estadísticas reales ni botones de estadísticas en la tarjeta**, por no existir confirmación del conjunto de los cuatro IDs y disponibilidad en la categoría consultada. Este trabajo prepara el motor oficial único para tarjetas bajo demanda y sincronización opt-in; no activa ninguna de ellas automáticamente.


## 09/11/2026 — Comprobación cruzada de los cuatro identificadores en la APK

El APK 5.0.42 entregado se examinó **directamente** en `base.apk/classes2.dex`, leyendo los `field_ids` de `JugadorDetalleResponseDto`, `DetalleJugadorDto` y `EquipoDetalleDto`. Los campos relevantes realmente definidos por el modelo son:
- `jugador.id` desde `DetalleJugadorDto.id`.
- `equipo.id` desde `EquipoDetalleDto.id` del objeto `JugadorDetalleResponseDto.equipo`.
- `idComponenteClub` y `idTemporadaActual` en la raíz de `JugadorDetalleResponseDto`.
Este **vínculo de datos** es más fuerte que inferir la temporada desde una etiqueta textual. Su presencia en el DTO no confirma que el servidor entregue el objeto `equipo` para toda ficha/categoría.

Implementación nueva (solo `dev`):
- `player_context.py`: `verified_player_stats_context(raw, player_id, team_id)` exige respuesta de detalle sin error, jugador y equipo con IDs exactamente coincidentes y dos IDs de componente/temporada no vacíos. No devuelve nombres, imagen ni respuesta cruda, y no hace suposiciones.
- `player_statistics_bridge.py`: ejecuta primero la ficha; **si no demuestra esa relación no solicita estadísticas**. Si la valida, construye los dos formularios de la APK (`datosGlobalesJugadorEquipo` y `datosMediasJugadorPartidos`), ambos normalizados sin inventar valores. Si falla la respuesta global, no hace la petición posterior.
- El transporte autorizado de `/v2/jugador.ashx` ya acepta únicamente `detalleJugador` y las dos acciones estadísticas con su conjunto exacto de campos; el adaptador `AficionFBMAdapter.player_statistics` conserva el detalle bruto transitoriamente dentro del método, sin volcarlo en caché ni WebSocket. `IndependentClient.async_player_statistics` cachea exclusivamente resultado normalizado por **par jugador/equipo** y TTL de 120 segundos. Expuesto como comando administrador `fbm/player/stats` solo bajo petición explícita, no activado en tarjetas.
- Tests independientes en `test_player_context.py` y `test_player_statistics_bridge.py`, más pruebas del adaptador y puente WS, verifican asociación y bloqueo de solicitudes ante IDs cruzados, ausentes o respuestas inválidas. No se ha desplegado en Home Assistant ni ejecutado tráfico contra FBM real.
- Advertencia: la API devuelve estadísticas individuales potencialmente asociadas a menores. No se almacena histórico ni se sincroniza automáticamente; antes de habilitar visualización hay que comprobar respuestas y restricciones reales de la competición. Este paso **no valida todavía la consulta contra el servidor**; valida la lógica y el protocolo de APK con simulaciones.


## 10/11/2026 — Estado HA real y corrección de respuesta tardía en tarjetas independientes

**Comprobación real por Home Assistant MCP (solo lectura):** integración `fbm` existente `01M7066AYTB3VE4BSVXG27X5R1` en estado **loaded**. No se instaló ningún backend nuevo ni se usaron credenciales. La instalación actual no incluye las nuevas rutas `fbm/team/schedule_probe`, `fbm/team/players` y `fbm/player/stats`, por lo que **no se ha validado tráfico real de esas acciones**. Las pruebas CI solo prueban contratos, rechazos y orquestación con simulaciones.

Se volvió a inspeccionar el ZIP real de la APK facilitada `Afición FBM-5.0.42-split-apks(1).zip` SHA256 `31ac162e717dd045870c3cbf1cb22f64e5ba3dedc93d31600c4e8acbf61df099`. `base.apk` incluye `classes.dex` 8.819.220 B y `classes2.dex` 9.003.808 B. Campos del DTO `JugadorDetalleResponseDto`: `jugador`, `equipo`, `idComponenteClub`, `idTemporadaActual`; `DetalleJugadorDto.id` y `EquipoDetalleDto.id` son `String`, respaldando la comprobación exacta sin inferir identificadores.

**Corrección frontend detectada en revisión:** una petición de plantilla `fbm/team/players` podía terminar después de un cambio de equipo y guardar datos de la selección anterior en el estado de la tarjeta. Rama DEV: `fbm-card.js` commit `b997517` y copia empaquetada `custom_components/fbm/www/fbm-card.js` commit `3e63ec5` comprueban que `selected` y `entry` sigan coincidiendo antes de aceptar la plantilla. Al actualizar la plantilla descartan también la ficha individual anterior. Regresiones en `tests/card.test.cjs` commit `bf36744`: respuesta tardía ignorada y ficha anterior borrada. Dos workflows de `bf36744` SUCCESS: https://github.com/sergey08/Fbm-card/actions/runs/42717399246 y https://github.com/sergey08/Fbm-card/actions/runs/42717390850.

**Siguiente paso necesario (sin fingir éxito):** instalar en una prueba controlada backend + JS del mismo commit DEV preservando `.storage` e identidad; con la sesión registrada consultar `fbm/team/schedule_probe` y `fbm/team/players`. Si FBM confirma las respuestas, validar `fbm/player/detail` y `fbm/player/stats` con restricciones de disponibilidad/privacidad. No activar seguimiento automático. No hay aún calendario ni estadísticas reales verificadas, ni despliegue realizado. `main` y tarjetas instaladas de Gael y Zoe intactas.
