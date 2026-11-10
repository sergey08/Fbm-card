# FBM Card v0.2.2b6 — Beta / Arranque fiable del diagnóstico

## English
- Fix initial `sensor.competiciones` polling so automatic refresh options and scheduler are initialized **before** the sensor platform is forwarded. This avoids the incorrect transient `groups_enabled=false` and `players_enabled=false` shown in b5 immediately after startup, even when both settings are saved as enabled.
- No modifications to existing archived competitions, schedules, classifications, player data, or the stable JavaScript card.
- Existing opt-in schedule is unchanged: one followed group every 4 hours and up to five player records every 2 hours, with the existing 24-hour end-of-cycle pause.
- The sensor continues to expose a small `automatic_refresh` diagnostic with enabled settings, last attempted execution, and bounded result labels, without personal player data.
- Tests: DEV commit `ac82b47` passed FBM validation (run `42913883930`) and real Home Assistant Core API smoke (run `42913883895`). The isolated beta publisher additionally checks Python, Node and real Home Assistant API before creating the prerelease.
- A successful installation is **not** proof that the recurring FBM requests have run. After upgrading, inspect `sensor.competiciones.attributes.automatic_refresh`. It is normal for `last_run` to remain null until the next scheduled interval.

## Español
- Corregido el primer sondeo de `sensor.competiciones`: primero se cargan las opciones de actualización automática y se inicializa el programador, **después** se inicia la plataforma del sensor. Esto evita que b5 muestre transitoriamente `groups_enabled=false` y `players_enabled=false` aunque las casillas estén guardadas como activadas.
- Sin cambios en las competiciones archivadas, calendarios, clasificaciones, datos de jugadores ni JavaScript de la tarjeta estable.
- Se mantienen las opciones voluntarias: un grupo seguido cada 4 horas y un máximo de cinco registros de jugadores cada 2 horas, con pausa de 24 horas al completar una ronda.
- El atributo `automatic_refresh` sigue mostrando los interruptores, el último intento y estados resumidos sin exponer datos personales.
- Validación de DEV `ac82b47`: pruebas FBM `42913883930` correctas y prueba de API real de Home Assistant Core `42913883895` correcta. El workflow de publicación volverá a comprobar ambas suites antes de crear la prerelease.
- Instalar correctamente no demuestra que ya haya habido una consulta periódica. Revisar `sensor.competiciones.attributes.automatic_refresh`; `last_run=null` es normal hasta que transcurra el primer intervalo.

## Installation / Instalación
Optional prerelease. Confirm a recent Home Assistant backup, download exactly `v0.2.2b6` from Marketplace and restart Home Assistant. The existing automatic refresh preferences must be preserved. Avoid enabling scheduled FBM requests unless desired.

Beta opcional. Comprueba que exista una copia de seguridad reciente, descarga explícitamente `v0.2.2b6` en Marketplace y reinicia Home Assistant. Las preferencias automáticas previamente guardadas deben conservarse.

## Rollback / Reversión
Reinstall `v0.2.2b5` and restart; this release does not intentionally change SQLite schema.
Reinstala `v0.2.2b5` y reinicia; esta versión no cambia intencionadamente el esquema de SQLite.
