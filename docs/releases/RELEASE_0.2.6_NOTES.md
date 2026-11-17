# FBM Card 0.2.6 — Actualización automática de partidos

## Mejoras
- Se elimina el botón **Actualizar partidos** de las tarjetas de equipo.
- Al pulsar **Partidos**, el calendario se consulta automáticamente si no está disponible.
- Si los datos se obtuvieron de la consulta remota, se actualizan al volver a entrar cuando hayan transcurrido al menos 15 minutos desde la última consulta.
- Se evita iniciar otra consulta mientras haya una en curso.
- Se conservan las fases, jornadas, filtros de fechas y los datos archivados; las tarjetas que usan archivo local no fuerzan consultas remotas.
- Continúa identificándose como **FBM Card (no oficial)**.

## Instalación
Actualiza desde Marketplace/HACS y reinicia Home Assistant. No elimines la integración ni su configuración.
