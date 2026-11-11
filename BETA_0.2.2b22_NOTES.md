# FBM Card v0.2.2b22 (Beta) — Incremental refresh and scoring coverage

## English

### Main changes
- **All followed competitions** are processed by the automatic coordinator in a bounded rotation. The coordinator checks one competition per hour; a remote group refresh is due when an archived fixture falls within ±2 days of today (minimum 4-hour interval) or at least once every 7 days otherwise. A missing initial check also triggers a refresh.
- Refresh team rosters only when completed match IDs/scores have changed or a followed team has no roster archived.
- Inspect up to **five players every 30 minutes**, preserving the existing cursor across teams and competitions. Skip remote individual-stat queries when the archived unique scored match IDs already cover official roster appearances. Explicit administrator refresh remains available.
- Publish `groups[].last_checked_at` (public team-level metadata only) in `sensor.competiciones` to distinguish a recent check with no changes from an old snapshot. No player IDs or private data are added to the public sensor.
- Add `cobertura_anotacion` to group analysis: roster size, players with scored matches, points attributed to individual records, points scored in finished team fixtures, unmatched points and whether totals reconcile. Match IDs are matched and deduplicated to prevent false claims of completeness.
- Preserve the existing SQLite archive, followed competition identities, admin-only individual data, card resources and previous WebSocket commands.
- Add Python regression tests, JavaScript regression tests and Home Assistant Core 2026.11 API smoke suite.

### Scope and limitations
- Incremental is **change-driven after observing an official result or appearance-count change**; a corrected historical individual score without an added appearance may require explicit administrator refresh. The policy also performs periodic fixture checks for late score corrections. This is not a guaranteed live push notification from FBM.
- A successful batch means **only that batch** completed; full competition coverage is assessed separately, and a player with a score of zero is not missing if a numeric score was recorded.
- On first use, missing team rosters are backfilled when their groups are visited. It may take more than one rotation to fill all players; existing downloaded stats are not deleted.
- If a group changes phase or season, it is not enrolled silently. The administrator must explicitly follow the new verified identity.
- The supplied Valdemoro and Santa María del Pilar crests belong to the user-approved scouting report design and are **not embedded into this integration**.

### Installation / rollback
Prerelease only. After CI validation and confirmation that `v0.2.2b22` is published, choose the exact beta in HACS/Marketplace and restart HA. Check `sensor.competiciones` for all four followed competitions, new `last_checked_at` fields, and aggregate scorer coverage from `fbm/competition/analysis`. Verify no unexpected extra requests and no loss of SQLite snapshots. Return to `v0.2.2b21` if necessary while preserving HA backup and archived data.

## Español

### Cambios
- **Todas las competiciones seguidas** participan en la rotación automática. Se revisa un grupo por hora, pero solo se consulta FBM si existe un partido conocido dentro de ±2 días (mínimo 4 horas desde la última consulta de ese grupo), si toca revisión de seguridad de 7 días o si nunca se ha comprobado.
- Las plantillas se consultan solo si cambian los partidos finalizados o falta alguna plantilla archivada.
- Se inspeccionan hasta **cinco jugadores cada 30 minutos** con cursor persistente por grupo/equipo; se omiten peticiones individuales cuyos partidos archivados ya cubren las apariciones oficiales registradas en la plantilla.
- Se incorpora `groups[].last_checked_at` en `sensor.competiciones` para diferenciar la última comprobación de la última actualización real del archivo.
- El análisis añade `cobertura_anotacion`: jugadores en plantilla, jugadores con puntos por partido, puntos atribuidos, puntos del marcador, diferencia y cobertura completa/incompleta. Evita duplicados y distingue cero de datos ausentes.
- Se conservan la base SQLite, los grupos seleccionados, los comandos WebSocket administrativos y las tarjetas sin cambios.
- Pruebas Python, JavaScript y Home Assistant Core 2026.11 añadidas/actualizadas.

### Límites
No existe notificación push confirmada desde FBM: las novedades se detectan en comprobaciones periódicas. Las correcciones posteriores de estadísticas individuales sin cambio en el número de partidos pueden requerir una sincronización administrativa expresa. Un lote correcto no acredita que todos los jugadores o equipos estén completos; revisar los indicadores de cobertura. Una nueva fase o temporada no se sigue automáticamente.

### Instalación y vuelta atrás
Publicar únicamente después de superar CI; seleccionar exactamente `v0.2.2b22` desde HACS/Marketplace y reiniciar. Confirmar los cuatro grupos, el progreso por grupo y la cobertura estadística mediante el MCP. Conservar copia de seguridad y la posibilidad de volver a `v0.2.2b21`, sin borrar SQLite.
