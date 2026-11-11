# FBM Card 0.2.2b14 (Beta)

## English

- The competition team header reuses the club crest retrieved for matchdays. The view accepts the same official crest references as the fixed-team card, including long encoded references returned by FBM.
- Matchday crest lookup accepts calendar ranges longer than the FBM query limit by requesting a bounded initial window. Archived fixtures and results remain intact.
- Confirming a followed competition starts its first standings and fixture sync immediately. Player rosters stay optional. If the sync fails, the selection is kept and the form shows an error so it can be retried.

## Español

- La cabecera del equipo reutiliza el escudo recuperado para las jornadas. La tarjeta admite las mismas referencias oficiales que la de equipo fijo, incluidas las referencias largas codificadas de FBM.
- La consulta de escudos toma un intervalo inicial válido cuando el calendario supera el límite de FBM. Se conservan los partidos y resultados archivados.
- Al confirmar el alta de una competición se inicia la descarga de clasificación y partidos. Las plantillas siguen siendo opcionales. Si falla la sincronización, el grupo queda guardado y el formulario permite reintentar.

Instala desde HACS, reinicia y recarga el panel. Si se mantiene la interfaz anterior, actualiza el recurso existente a `/fbm_static/fbm-card.js?v=0.2.2b14`.
