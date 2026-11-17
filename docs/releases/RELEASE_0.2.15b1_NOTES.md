# FBM Card v0.2.15b1

## English

Initial competition downloads now process consecutive batches of up to five players, with a two-second pause between batches and the existing half-second pause between queried players. Downloads start automatically once rosters are available after following a competition, and resume from the last committed batch after restart.

Player requests share a lock with scheduled maintenance. Errors increase the pause from ten seconds up to five minutes. Each failed batch is retried once before moving forward, while missing data remain pending for subsequent scheduled passes. Coverage updates after each batch.

Automated tests cover a complete two-team SQLite download, restart, error backoff, unload cancellation and unfollow. Live Home Assistant validation is pending. Install through HACS with prereleases enabled, select v0.2.15b1 and restart Home Assistant. Existing followed competitions with pending statistics are eligible immediately. To roll back, select v0.2.14 and restart.

## Español

La descarga inicial de competiciones procesa lotes consecutivos de hasta cinco jugadores, con dos segundos entre lotes y la pausa existente de medio segundo entre jugadores consultados. Arranca automáticamente cuando las plantillas están disponibles tras seguir una competición y continúa desde el último lote guardado después de un reinicio.

Las peticiones de jugadores comparten bloqueo con el mantenimiento programado. Los errores aumentan la pausa desde diez segundos hasta cinco minutos. Cada lote fallido se reintenta una vez antes de avanzar. Los datos que falten siguen pendientes para posteriores pasadas programadas. La cobertura se actualiza después de cada lote.

Las pruebas automáticas cubren la descarga completa de dos equipos en SQLite, reinicios, esperas ante errores, cancelación al descargar la integración y dejar de seguir el grupo. Falta validación funcional en Home Assistant. Instala desde HACS con versiones preliminares activadas, selecciona v0.2.15b1 y reinicia Home Assistant. Las competiciones ya seguidas con estadísticas pendientes pueden comenzar inmediatamente. Para volver atrás, selecciona v0.2.14 y reinicia.
