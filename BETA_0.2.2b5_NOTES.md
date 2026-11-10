# FBM Card v0.2.2b5 — Beta: automatic refresh health / Diagnóstico de actualización automática

## English — Changes since v0.2.2b4
- The existing `sensor.competiciones` exposes a small `automatic_refresh` attribute with enabled flags for groups and players, a bounded status, and the UTC timestamp of the latest attempted execution for each workstream. The sensor updates on its usual polling cycle (up to five minutes); these values are not live timers.
- Allowed execution labels are `pending`, `ok`, `partial`, `failed`, `no_followed_groups` and `no_standings` as appropriate. No player names, IDs, individual statistics, access tokens or remote error messages are exposed.
- Scheduler errors, including archive or cursor loading, no longer escape uncaught from the group or player refresh task. Previously saved snapshots are kept.
- Classification and fixtures remain on a 4-hour interval for one followed group at a time. Archived player statistics remain opt-in in batches of up to five every 2 hours, with a 24-hour full-cycle pause. These are unchanged from b4.
- Installed cards use precisely the stable 0.2.1 JavaScript bundle.
- Beta: automated tests do not replace observation of a complete scheduled cycle on a real Home Assistant installation. The initial diagnostic status may remain `pending` until the first interval elapses. Health values are in memory and reset after reload; the statistical cursor is still persistent.

## Español — Cambios respecto a v0.2.2b4
- El sensor actual `sensor.competiciones` añade el atributo `automatic_refresh` con las opciones activadas para grupos y jugadores, estado resumido y fecha UTC del último intento de cada tarea. La actualización del sensor se realiza en su ciclo habitual (hasta cinco minutos), no en tiempo real.
- Estados controlados: `pending`, `ok`, `partial`, `failed`, `no_followed_groups` y `no_standings` según el caso. No se muestran nombres ni identificadores de jugadores, estadísticas individuales, credenciales ni errores privados.
- Los fallos de consulta y de acceso a archivo SQLite o cursor se contienen en ambas tareas, conservando los datos guardados previamente.
- Se mantienen las frecuencias de b4: clasificación/calendario cada cuatro horas (un grupo seguido por ejecución) y estadísticas de un máximo de cinco jugadores cada dos horas, con pausa de 24 horas tras la ronda completa; ambas opciones siguen siendo voluntarias.
- El JavaScript de las tarjetas permanece idéntico al estable 0.2.1.
- Esta es una beta: los tests automatizados no sustituyen la verificación de un ciclo automático real. Al instalar puede aparecer `pending` hasta la primera ejecución. El diagnóstico en memoria se reinicia tras recargar la integración; el cursor de estadísticas sigue persistiendo.

## Installation / Instalación
This prerelease is optional. Make sure a recent full Home Assistant backup exists, install explicitly `v0.2.2b5` from Marketplace and restart Home Assistant. Do not enable additional competition/player options unless you intend scheduled network requests. Existing explicit choices are preserved.

Esta versión preliminar es voluntaria. Comprueba que exista una copia completa reciente, instala explícitamente `v0.2.2b5` desde Marketplace y reinicia Home Assistant. No actives opciones adicionales sin querer realizar consultas periódicas. Se conservan las opciones ya elegidas.

## Rollback / Reversión
Install `v0.2.2b4` (or stable `v0.2.1`) and restart. SQLite archive is not intentionally changed by this diagnostics-only beta.

Instala `v0.2.2b4` (o la estable `v0.2.1`) y reinicia. Esta beta de diagnóstico no modifica intencionadamente el esquema de SQLite.
