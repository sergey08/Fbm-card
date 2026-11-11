# FBM Card v0.2.2b9 — Automatic synchronization hotfix / Corrección de sincronización automática

## English

### Fixed
- **Home Assistant thread-safety regression:** scheduled group and player callbacks are now marked with `@callback`, so Home Assistant runs them on the event loop rather than dispatching them to an executor thread. This prevents the observed `RuntimeError: hass.async_create_task from a thread other than the event loop` in `competition_auto_sync.py`.
- Added a regression test for both native interval listeners, checking callback registration and that scheduled coroutines execute.
- Keeps the **b8 visual redesign** of the competition-following card, the team crest fallback, and the existing search/fixed-team cards.
- Preserves automatic synchronization opt-in settings, the local SQLite archive, saved competition selection, and existing Lovelace cards. No schema migration and no automatic re-enrollment.

### Verification
- Development branch: FBM Python/Node tests and real Home Assistant Core 2026.11 smoke tests passed.
- **Runtime verification still required after installing b9:** with automatic group and player options enabled, check `sensor.competiciones.attributes.automatic_refresh` and confirm `last_run` becomes populated after the corresponding timer. Group interval: **4 hours**; players: **2 hours**. A restart resets the timer windows. A `pending` state immediately after restart is expected; it is not evidence of success.
- Inspect Home Assistant system logs to ensure the thread-safety error no longer occurs. Old historical log entries may remain.
- If the upstream FBM API is unavailable, a job may report `failed` or `no_followed_groups`; that is separate from the event-loop fix.

### Install
1. Ensure a recent HA backup. Marketplace → FBM → Download again → select `v0.2.2b9`.
2. Restart Home Assistant.
3. Update the **existing** Lovelace JavaScript resource (do not add another): `/fbm_static/fbm-card.js?v=0.2.2b9`. Reload the Android app.
4. Keep the existing competition card YAML:
```yaml
type: custom:fbm-competition-card
title: Competición FBM
entity: sensor.competiciones
group_index: 0
```

### Rollback
Reinstall `v0.2.2b8`, restart HA and change the existing Lovelace resource query to `?v=0.2.2b8`. Note that b8 still contains the scheduled synchronization thread-safety defect; disable the automatic refresh options if temporarily rolling back.

## Español

### Corregido
- **Error de seguridad de hilos en Home Assistant:** los temporizadores de grupos y jugadores llevan ahora `@callback` para ejecutarse en el bucle principal de HA, en vez de un hilo de trabajo. Corrige el error real `RuntimeError: hass.async_create_task from a thread other than the event loop` detectado en `competition_auto_sync.py`.
- Nueva prueba de regresión para ambos temporizadores: registro como callbacks y lanzamiento de tareas asíncronas.
- Se mantiene **el rediseño visual de b8** de la tarjeta de competiciones, los escudos con icono alternativo y las tarjetas anteriores de búsqueda/equipo fijo.
- Se conservan las dos opciones de actualización automática, el archivo SQLite, la selección de competición y las tarjetas Lovelace. Sin migración de esquema ni nuevas altas automáticas.

### Verificación
- Superadas en desarrollo las pruebas FBM Python/Node y el test real de Home Assistant Core 2026.11.
- **Pendiente validar en tu HA tras instalar b9:** con ambas opciones activas, revisar `sensor.competiciones.attributes.automatic_refresh` y comprobar que `last_run` se rellena al ejecutar los temporizadores. Grupos: cada **4 horas**; jugadores: cada **2 horas**. Al reiniciar empiezan de nuevo los intervalos. Ver `pending` justo después de reiniciar es normal y no confirma que funcione.
- Revisar el registro de HA para confirmar que no aparecen nuevas incidencias de seguridad de hilos. Los errores antiguos pueden seguir visibles.
- Si la FBM no responde, el trabajo puede quedar `failed` o `no_followed_groups`, problema distinto de este arreglo.

### Instalación
1. Confirma una copia de seguridad reciente. Marketplace → FBM → Descargar de nuevo → selecciona `v0.2.2b9`.
2. Reinicia Home Assistant.
3. Actualiza el **recurso JavaScript existente** de Lovelace (sin duplicarlo): `/fbm_static/fbm-card.js?v=0.2.2b9`. Vuelve a abrir la aplicación Android.
4. Mantén el YAML actual de la tarjeta de competiciones:
```yaml
type: custom:fbm-competition-card
title: Competición FBM
entity: sensor.competiciones
group_index: 0
```

### Reversión
Reinstala `v0.2.2b8`, reinicia HA y devuelve el recurso existente a `?v=0.2.2b8`. Atención: b8 todavía contiene el fallo de hilos del programador; desactiva las opciones de sincronización automática si necesitas volver temporalmente.
