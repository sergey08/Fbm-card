# FBM Card v0.2.2b23 (Beta) — Player batch retries and diagnostics

## English

This beta builds on v0.2.2b22's event-aware incremental synchronization for all followed FBM competitions.

### Improvements
- A player statistics batch that reports a **partial** failure is retried **once at the next scheduled tick** (30 minutes later), without increasing the **five-player maximum** per tick.
- If the retry still fails, the cursor advances so one problematic record cannot block subsequent teams and competitions.
- Player sync health includes privacy-safe, aggregate numeric fields: `processed`, `saved`, `skipped_unchanged`, `errors`, `players_without_match_data`, `retry_pending`. These are persisted across restarts and exposed through `sensor.competiciones` automatic-refresh attributes.
- No player names, player IDs, diagnostic messages, raw private FBM records or photos are published in health attributes.
- Existing competition and roster snapshots remain intact; no archive schema changes.
- Includes regression tests for single retry, successful retry, and persistent privacy-safe health, plus actual Home Assistant Core API validation.

### Notes
A partial batch may result from transient network/API conditions or an unavailable/malformed official record. Aggregate counters cannot identify its underlying cause; they help distinguish transient and persistent failure. This beta does not force a full re-download of archived competition data. Backups and rollback to v0.2.2b22 remain advisable.

## Español

Esta beta continúa el sistema incremental de todas las competiciones seguidas de v0.2.2b22.

### Mejoras
- Si un lote de estadísticas devuelve estado **partial**, se reintenta **una sola vez en la siguiente ejecución programada** (30 minutos después). Se mantiene el límite de **cinco jugadores por ejecución**.
- Si el reintento también falla, el cursor avanza para impedir que una ficha defectuosa bloquee las restantes competiciones.
- Nuevos contadores agregados de diagnóstico en `sensor.competiciones`, conservados tras reiniciar: `processed`, `saved`, `skipped_unchanged`, `errors`, `players_without_match_data` y `retry_pending`.
- No se publican nombres, identificadores de jugadoras/es, mensajes de error privados ni fotos en los atributos del sensor.
- No modifica el esquema SQLite ni borra datos; conserva las consultas y tarjetas existentes.
- Pruebas de regresión de reintentos y privacidad, además de verificación con Home Assistant Core real.

### Limitaciones
El estado parcial puede deberse a errores transitorios o registros oficiales no disponibles. Los contadores ayudan a diagnosticar, pero no identifican por sí solos el origen exacto. No se ejecutan sincronizaciones masivas forzadas. Se recomienda copia de seguridad y mantener disponible la vuelta a v0.2.2b22.
