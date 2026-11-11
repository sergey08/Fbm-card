# FBM Card 0.2.2b12 (Beta)

## English

- The competition card shows the official FBM category when known and identifies each followed group in a selector. The selection survives a change in group order. Groups without an archived table show a pending message.
- The competition team detail now shares the fixed-team fixture and player layouts. Fixture cards show date, venue, score and available verified club crests. Player cards use the same profile and statistics controls with archived sporting data. The archive does not contain player photographs.
- Existing archives open as before. If the official category or club crests are missing, refresh the followed group to populate available metadata. The reference team identifies a group while its category is unavailable.

Install the beta through HACS and restart Home Assistant. If the old interface is cached, update the existing dashboard module to `/fbm_static/fbm-card.js?v=0.2.2b12` and reload.

## Español

- La tarjeta muestra la categoría oficial de FBM cuando está disponible y permite elegir entre los grupos seguidos. La selección se conserva si cambia el orden de los grupos. Los grupos sin clasificación archivada muestran un aviso de sincronización pendiente.
- El detalle de competición comparte el diseño de partidos y jugadores de la tarjeta de equipo fijo. Los partidos muestran fecha, pabellón, marcador y escudos oficiales disponibles. Las fichas de jugadores usan los mismos controles y estadísticas deportivas archivadas. El archivo omite las fotos de jugadores.
- Los archivos existentes siguen siendo compatibles. Si faltan la categoría oficial o los escudos, sincroniza el grupo seguido para incorporar los datos que facilite FBM. Mientras falta la categoría, el selector identifica el grupo por su equipo de referencia.

Instala la beta desde HACS y reinicia Home Assistant. Si el navegador conserva la interfaz anterior, cambia el recurso existente del panel a `/fbm_static/fbm-card.js?v=0.2.2b12` y recarga.
