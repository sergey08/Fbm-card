# FBM Card v0.2.2b28 — development notes / notas de desarrollo

## English
**Status: development branch, not released or installed.**

- Introduces read-only per-competition coverage counters in `sensor.competiciones` under `coverage`.
- Counts teams with standings, archived and missing rosters, players with at least one appearance, complete individual statistics, and pending/incomplete statistics. Coverage percentage is withheld while rosters are missing.
- Uses the same completion rule as differential synchronization: distinct official match IDs and integer points for each match.
- Only followed groups are inspected; no external requests, no player names or identifiers in coverage output, no SQLite writes.
- Added offline regression tests for absent databases, followed-only filtering, duplicate match IDs and zero-appearance players.
- **Limitations:** a roster not yet downloaded is counted as a missing roster, not as a known number of missing players; totals are lower bounds until all rosters are archived. CI and live HA validation pending.

## Español
**Estado: rama de desarrollo; no publicada ni instalada.**

- Añade contadores de cobertura por competición, de solo lectura, en el atributo `coverage` de `sensor.competiciones`.
- Cuenta equipos en clasificación, plantillas archivadas y ausentes, jugadores con al menos una aparición, estadísticas individuales completas y estadísticas pendientes/incompletas. No muestra porcentaje de cobertura mientras falten plantillas.
- Aplica el mismo criterio que la sincronización diferencial: identificadores únicos de partido y puntos enteros por partido.
- Solo analiza competiciones seguidas; sin peticiones externas, sin nombres ni identificadores de jugadores en el resumen y sin escrituras SQLite.
- Pruebas offline para base de datos ausente, filtrado de grupos favoritos, partidos duplicados y jugadores sin partidos.
- **Limitaciones:** las plantillas aún no descargadas cuentan como plantillas ausentes, no como un número conocido de jugadores pendientes; los totales son mínimos hasta completar las plantillas. CI y validación real en HA pendientes.

## Next / Próximo
- Verify full CI and HA Core smoke before preparing the prerelease.
- Check actual counters on all five followed competitions.
- Add a visual progress indicator and direct competition selection in a subsequent iteration.
