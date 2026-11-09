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
