# FBM Card 0.2.2b13 (Beta)

## English

- The competition dropdown stays open during Home Assistant state refreshes.
- Matchday cards use official fixture images from the regular team schedule when the local archive lacks crests. The archived scores and fixtures are preserved.
- Opening Players loads available photos from the same FBM roster query used by the team cards. Photos are used in memory and not written to the competition archive. Live images require a working FBM session.

Install b13 in HACS, restart Home Assistant and reload the dashboard. If needed, change the existing module URL to `/fbm_static/fbm-card.js?v=0.2.2b13`.

## Español

- El selector de competiciones permanece abierto durante las actualizaciones de estado de Home Assistant.
- Las jornadas consultan los escudos oficiales del calendario habitual de equipos cuando faltan en el archivo local. Conservan los partidos y marcadores archivados.
- Al abrir Jugadores, la tarjeta carga las fotos disponibles con la misma consulta de plantilla que usan las tarjetas de equipo. Las fotos se muestran en memoria y no se guardan en el archivo de competiciones. Las imágenes en directo requieren una sesión de FBM operativa.

Instala b13 desde HACS, reinicia Home Assistant y recarga el panel. Si hace falta, cambia la URL del módulo existente a `/fbm_static/fbm-card.js?v=0.2.2b13`.
