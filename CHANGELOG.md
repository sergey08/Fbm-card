# Changelog

## Unreleased

- Confirming a new competition enables background synchronization and retries automatically.

- Competition refresh reports partial progress when a roster download fails.
- A group awaiting standings no longer blocks statistics downloads for other groups after a restart.
- Roster downloads save each completed team immediately. When the results are unchanged, subsequent incremental passes request only missing rosters.

## Sin publicar

- Confirmar una competición nueva activa automáticamente la sincronización en segundo plano y sus reintentos.

- La actualización de la competición indica un estado parcial si falla la descarga de alguna plantilla.
- Un grupo pendiente de clasificación deja avanzar la descarga de estadísticas de los demás grupos después de un reinicio.
- Se guarda cada plantilla al terminar su descarga. Si los resultados no cambian, las siguientes pasadas incrementales solo consultan las plantillas que faltan.
