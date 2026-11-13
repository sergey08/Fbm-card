# FBM Card v0.2.2b27 (Beta) — Player coverage diagnostics and priority bootstrap

## English

### Improvements
- Prioritize followed competitions with the most missing or incomplete player match statistics at the beginning of each player synchronization cycle.
- Detect newly followed or removed groups, reset the saved player cursor, and bypass the 24-hour completed-cycle delay. Download still respects the five-player batch limit and the 30-minute schedule.
- Keep the selected priority group pinned throughout the current pass, preventing unstable reordering as new snapshots arrive.
- Add privacy-safe diagnostic counters for players queried, zero-appearance players, complete and incomplete cached statistics, and missing match points. Restore counters after Home Assistant restarts.
- Retain the incremental/differential archive, weekly revalidation, official FBM data provenance, and existing safeguards against inventing unavailable scores.

### Validation
- Full offline Python test suite: 374 tests passed.
- JavaScript regression tests and source consistency: passed.
- Home Assistant Core 2026.11.0 integration smoke test: passed.
- GitHub Actions run: https://github.com/sergey08/Fbm-card/actions/runs/43515014195

### Notes
- Automatic priority begins on the next scheduled player sync, not instantly when a group is followed.
- Officially missing or inconsistent individual statistics are reported; no fabricated figures are inserted.

## Español

### Mejoras
- Se priorizan las competiciones seguidas con más estadísticas individuales ausentes o incompletas al comenzar cada ciclo de jugadores.
- Se detectan cambios en los grupos seguidos, se reinicia el cursor de jugadores y se evita la espera de 24 horas tras un ciclo terminado. Se mantienen los lotes de hasta cinco jugadores y la frecuencia de 30 minutos.
- La competición prioritaria permanece fijada durante el recorrido para evitar cambios de orden mientras llegan nuevos datos.
- Nuevos contadores de diagnóstico, sin información personal, para jugadores consultados, sin partidos, estadísticas completas o incompletas en caché y puntos por partido ausentes. Los contadores se restauran tras reiniciar Home Assistant.
- Se conservan el histórico incremental y diferencial, la revisión semanal y las garantías de no inventar datos oficiales de FBM.

### Validación
- Suite offline Python: 374 pruebas superadas.
- Pruebas JavaScript y coherencia de archivos: superadas.
- Prueba de integración con Home Assistant Core 2026.11.0: superada.
- GitHub Actions: https://github.com/sergey08/Fbm-card/actions/runs/43515014195

### Observaciones
- La prioridad comienza en la siguiente ejecución programada de sincronización, no inmediatamente al seguir una competición.
- Los datos individuales no publicados o inconsistentes se señalan sin rellenarlos con valores inventados.
