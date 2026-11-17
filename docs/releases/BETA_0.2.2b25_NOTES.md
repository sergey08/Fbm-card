# FBM Card v0.2.2b25 (Beta) — Match-by-match score auditing

## English

### Improvements
- Adds **match-specific scorer coverage checks** in the existing administrator-only `fbm/competition/analysis` response.
- New aggregate fields: `partidos_con_desajuste_individual` and `incidencias_anotacion_partidos` (bounded to 40 cases), reporting each match date, teams, official scores, sums of archived individual points, number of player match records, unmatched points, and whether both teams' totals disagree.
- Uses verified finished fixture IDs and deduplicates repeated player-game rows. If no individual data are archived, coverage remains **unknown**, not zero.
- Retains v0.2.2b24 incremental syncing, zero-appearance skip, bounded retry, scheduling, existing HA cards and SQLite data unchanged.
- No raw match DTOs or individual player names/IDs appear in this new aggregate diagnostic. Python/JS and actual Home Assistant Core checks are required.

### Verified source discrepancy
On 17 October 2026 the official match record (confirmed by live FBM schedule query and existing archive) shows **C.D.B. Colegio Áquila 115 – 96 PA La Kaseta Ciempobasket**. Archived player-point rows sum **4 – 3** for the same fixture. Other archived games for these teams reconcile. Root cause is still **unverified**; no official score is altered and no missing points are inferred. The new feature makes this detectable instead of silently trusting all apparent individual percentages.

### Deployment
Beta/prerelease. Keep a Home Assistant backup before installing. Revert to v0.2.2b24 if needed. Full source data retained; no SQLite migration.

## Español

### Novedades
- Incorporada **auditoría de anotación por partido** a la respuesta administrativa `fbm/competition/analysis`.
- Campos nuevos `partidos_con_desajuste_individual` e `incidencias_anotacion_partidos` (hasta 40 incidencias), con fecha, equipos, puntos del marcador, puntos individuales archivados, número de registros por equipo, diferencia y detección de desajuste bilateral.
- Comprueba los IDs oficiales de los partidos terminados, evita duplicados y trata los datos individuales ausentes como **desconocidos**, no como cero.
- Conserva intactos el sincronizador incremental b24, los reintentos, la exclusión de jugadores con cero partidos, las tarjetas y el historial SQLite.
- No muestra nombres o identificadores individuales en la nueva auditoría agregada; pruebas Python, JavaScript y Home Assistant Core obligatorias.

### Incidencia de origen todavía pendiente
Encuentro del **17/10/2026: C.D.B. Colegio Áquila 115 – 96 PA La Kaseta Ciempobasket**. El calendario oficial consultado en directo coincide con el archivado, pero las estadísticas por jugador suman **4 – 3**. Los otros partidos archivados de ambos equipos cuadran. **No se ha demostrado aún la causa**: no se corrige el resultado ni se inventan puntos. Esta beta sirve para detectar y comunicar con precisión discrepancias similares en cualquier competición seguida.

### Instalación y vuelta atrás
Versión beta. Conservar copia de seguridad de HA y opción de regresar a v0.2.2b24. No hay migración de base de datos.
