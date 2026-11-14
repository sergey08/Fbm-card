# FBM Card 0.2.2b21 (Beta) — Persistent automatic refresh diagnostics

## English

### What's new
- Preserve the status and last execution timestamp for **group** and **player** automatic refreshes across Home Assistant restarts.
- Restore only validated, bounded status metadata from the existing private Home Assistant Store; no player names, photos, raw FBM responses, secrets or identifiers are stored as health data.
- Merge concurrent status updates without losing the other workstream's health or existing refresh cursors.
- Continue operation if diagnostic storage cannot be read or written. Sync frequency remains **every 4 hours for groups** and **every 2 hours for a batch of up to 5 players** when explicitly enabled.
- Includes regression tests for restart recovery, invalid saved health, cursor preservation and concurrent group/player status merging.
- Keeps the v0.2.2b20 admin-only archived `fbm/competition/match_preview` WebSocket feature unchanged. No dashboard/JavaScript card changes and no SQLite schema changes.

### Validation and rollout
This candidate is not installed automatically. After successful full Python, JavaScript and Home Assistant Core 2026.11 validations and confirmation of the GitHub prerelease, select **v0.2.2b21** explicitly in Home Assistant Marketplace/HACS, restart Home Assistant, and verify `sensor.competiciones.attributes.automatic_refresh`. Before restart, note the latest completed `groups` / `players` status and `last_run`; after restart those values should persist. A new installation with no previously saved health legitimately starts with `pending` until the first timed refresh. Existing health from earlier versions was memory-only and cannot be reconstructed retrospectively.

The patch does **not** force a refresh, change timers, copy player data into public sensors, or guarantee that both timers have run. Verify actual group and player cycles independently. If any issue appears, reinstall `v0.2.2b20` without deleting the existing FBM SQLite archive or guest identity; keep a Home Assistant backup before updating.

## Español

### Novedades
- Se conservan el estado y la última hora de ejecución de la actualización automática de **grupos** y **jugadores** después de reiniciar Home Assistant.
- Solo se recuperan metadatos de diagnóstico validados y acotados en el almacenamiento privado ya existente. No se guardan como diagnóstico nombres de menores, fotografías, respuestas FBM, secretos ni identificadores.
- Las actualizaciones concurrentes no eliminan los estados de la otra tarea ni los cursores de progreso.
- Un error al leer o guardar estos indicadores no detiene el planificador. Se mantienen los intervalos de **4 horas para grupos** y **2 horas para lotes de hasta 5 jugadores** cuando el usuario los tiene activados.
- Pruebas nuevas de recuperación tras reinicio, estados inválidos, conservación de cursores y escritura concurrente.
- Permanece intacto el comando administrativo `fbm/competition/match_preview` incorporado en v0.2.2b20. No hay cambios de tarjetas JavaScript ni del esquema SQLite.

### Validación e instalación
Esta candidata no se instala automáticamente. Tras las pruebas completas de Python, JavaScript y Home Assistant Core 2026.11 y la confirmación de la publicación en GitHub, elegir expresamente **v0.2.2b21** en Marketplace/HACS y reiniciar Home Assistant. Comprobar `sensor.competiciones.attributes.automatic_refresh`: si se observa una ejecución antes de reiniciar, su `status` y `last_run` deben conservarse después. Una instalación nueva sin estado persistido puede comenzar legítimamente en `pending` hasta que se cumpla el primer intervalo. Los indicadores de versiones anteriores estaban solo en memoria y no pueden reconstruirse retroactivamente.

La modificación **no** fuerza sincronizaciones, cambia temporizadores, publica datos de menores ni garantiza que ambos ciclos hayan tenido lugar. Hay que comprobar por separado el primer ciclo real de grupos y jugadores. En caso de incidencia, reinstalar `v0.2.2b20`, conservando SQLite, identidad invitada y copia de seguridad de Home Assistant.
