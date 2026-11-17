# FBM Card v0.2.2b24 (Beta) — Zero-appearance players

## English

### Changes
- Do not request FBM individual match statistics for roster members with **zero recorded appearances**. Official FBM may return an error-like payload for these entries; this is not a failed synchronization and must not incorrectly mark the batch as `partial`.
- Count such entries as skipped, without adding errors or exposing their names or IDs in public Home Assistant state. **When the roster records the first appearance, the usual incremental update automatically fetches that player's available statistics.**
- Retain b23's once-only retry for genuine partial batches, five-player cap, incremental group refresh, persisted progress, per-group checks and scoring coverage reconciliation.
- No SQLite migrations or card changes.
- Offline regression tests cover both the zero-game skip and newly eligible first appearance; all existing Python/JS and real Home Assistant Core tests are required.

### Data-quality caveat
Live FBM investigation of PA LA KASETA CIEMPOBASKET showed a **93-point discrepancy** in the completed game of October 17, 2026 against C.D.B. Colegio Áquila. Team fixture reports 96 scored; individual player records matching that official match ID sum only 3. The remaining three played games reconcile exactly. This release does **not** alter match scores or invent individual points; source data remains marked incomplete. The discrepancy is separate from the zero-appearance false errors.

### Rollback
Select `v0.2.2b23` if needed. Preserve the Home Assistant backup and existing archived FBM snapshots. Do not manually edit SQLite.

## Español

### Novedades
- No se consultan estadísticas individuales de jugadores cuya plantilla oficial señala **cero partidos jugados**. FBM puede devolver un error de respuesta para esas fichas, que no debe confundirse con una sincronización fallida ni generar un falso estado `partial`.
- Se contabilizan como omitidos sin revelar nombres ni identificadores personales en el sensor. **En cuanto conste su primer partido oficial, la sincronización incremental consultará automáticamente sus estadísticas.**
- Se conservan las mejoras de b23: un reintento para lotes parciales reales, límite de cinco jugadores, sincronización incremental de los grupos, conservación de cursores, fechas de última comprobación y cobertura de puntos.
- Sin cambios de estructura SQLite ni de las tarjetas; pruebas de regresión ampliadas.

### Limitación estadística detectada
El partido del **17/10/2026 entre PA LA KASETA CIEMPOBASKET y C.D.B. COLEGIO ÁQUILA** muestra 96 puntos a favor de Ciempobasket en el marcador, pero solo 3 puntos sumados en las estadísticas individuales vinculadas al ID de ese partido. Los otros tres partidos cuadran. **Faltan 93 puntos por atribuir en el origen archivado** y no se imputarán artificialmente. Esta discrepancia es distinta de los falsos errores de jugadores sin encuentros.

### Vuelta atrás
Se puede regresar a `v0.2.2b23` manteniendo una copia de seguridad. No manipular manualmente la base SQLite.
