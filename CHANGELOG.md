# Changelog

## v0.2.15b1 — English

- Download initial competition player statistics in consecutive five-player batches, paced by two-second pauses and the existing per-player delay.
- Start after following, startup or roster refresh. Persist initial progress separately from maintenance, resume after restart and stop on unload or unfollow.
- Back off progressively on errors, retry each failed batch once, then continue with other players. Incomplete data remain visible and eligible for subsequent scheduled retries.

## v0.2.15b1 — Español

- Descarga inicial de estadísticas de la competición con lotes consecutivos de cinco jugadores, pausas de dos segundos y la espera existente entre jugadores.
- Inicio al seguir una competición, arrancar la integración o actualizar las plantillas. Progreso persistente independiente del mantenimiento, reanudación tras reinicio y parada al descargar la integración o dejar de seguir el grupo.
- Espera creciente ante errores y un reintento por lote fallido antes de continuar. Los datos incompletos permanecen visibles y se reintentan en las pasadas programadas posteriores.

## v0.2.14 · English

- Recent results show the latest matchday with published scores, using the shared scoreboard and official crests.

## v0.2.14 · Español

- Últimos resultados muestra la jornada más reciente con marcadores publicados y utiliza el marcador compartido y los escudos oficiales disponibles.

## v0.2.13 · English

- Add an upcoming games tab to the competition card using archived fixtures.

- Compare archived final scores with the games played in official standings by team.

- Automatic calendar refresh queries the entire sporting year of the followed group.

- Confirming a new competition enables background synchronization and retries automatically.

- Competition refresh reports partial progress when a roster download fails.
- A group awaiting standings no longer blocks statistics downloads for other groups after a restart.
- Roster downloads save each completed team immediately. When the results are unchanged, subsequent incremental passes request only missing rosters.

## v0.2.13 · Español

- La tarjeta de competiciones incluye una pestaña de próximos partidos basada en el calendario archivado.

- Se comparan los marcadores finales archivados con los partidos jugados de cada equipo según la clasificación oficial.

- La actualización automática del calendario consulta todo el año deportivo del grupo seguido.

- Confirmar una competición nueva activa automáticamente la sincronización en segundo plano y sus reintentos.

- La actualización de la competición indica un estado parcial si falla la descarga de alguna plantilla.
- Un grupo pendiente de clasificación deja avanzar la descarga de estadísticas de los demás grupos después de un reinicio.
- Se guarda cada plantilla al terminar su descarga. Si los resultados no cambian, las siguientes pasadas incrementales solo consultan las plantillas que faltan.
