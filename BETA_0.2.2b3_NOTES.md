# FBM Card 0.2.2b3 — Beta de estadísticas individuales

## Cambios frente a 0.2.2b2
- Lotes manuales de **máximo cinco jugadores** para consultar datos deportivos por partido; exclusivamente administradores y competiciones ya seguidas
- Nuevos registros históricos de estadísticas en SQLite; no se guardan fotografías ni respuestas personales completas
- Si FBM no facilita los totales globales, se conservan como ausentes. Análisis por puntos publicados por partido, indicando la cobertura real
- El sensor estándar `sensor.competiciones` sigue mostrando únicamente equipos, clasificación y resultados
- Las tarjetas Lovelace existentes son idénticas a las de la versión estable

## Uso y seguridad
El comando de administrador `fbm/competition/player_stats_batch` requiere la competición, el equipo, la posición inicial y el tamaño del lote (1 a 5). No hay descarga masiva automática; permite avanzar controladamente por las plantillas ya archivadas. Se debe validar la descarga con FBM real antes de habilitar programación periódica.

## Recuperación
Versión preliminar voluntaria; copia de seguridad antes de instalar. Instalar `v0.2.2b3` desde Marketplace y reiniciar Home Assistant. Para revertir, reinstalar `v0.2.2b2` o la estable `v0.2.1`, y reiniciar. El fichero SQLite creado por versiones nuevas no es necesario para las anteriores.

## English
Adds admin-only, on-demand five-player per-match sports-statistics batches with SQLite snapshots and coverage-aware scoring analytics. No background collection, no minor profiles or images in ordinary HA sensors, Lovelace JavaScript unchanged. Explicit prerelease install/restart, revert by selecting the previous release.
