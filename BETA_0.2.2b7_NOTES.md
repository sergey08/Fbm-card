# FBM Card v0.2.2b7 — Competition Card / Tarjeta de competiciones

## English
### New competition-following card
- Adds `custom:fbm-competition-card`, independent from existing `custom:fbm-card` search and fixed-team cards.
- Read-only league standings from `sensor.competiciones`; tap a team to open its archived results, roster, and saved player statistics.
- On each team, filter archived fixtures by round (`Jornadas`) or view the complete available phase. Selecting a roster player shows only archived sports statistics and per-match details that were actually provided.
- Existing fixed-team cards prefer locally archived standings/fixtures to repeated network requests. The search card discovers the existing FBM integration session automatically. Opening the Players tab requests the roster when missing or older than 15 minutes; it does not require clicking “Actualizar plantilla”. Diagnostics are hidden by default.
- Public crest URLs are allowed only when FBM provides a complete, verified `https` URL under an allowlisted official host and appropriate image path. Missing, opaque or invalid references display a basketball fallback icon. **Not all team crests are guaranteed to appear.**
- Roster/player-stat read operations are administrator-only via WebSocket, validate followed competition membership, and read the local SQLite archive; opening a team in the new card never sends an extra request to FBM.
- Groups and players automatic-update settings remain opt-in, retained from b6. No intentional SQLite schema changes. No fabrication of missing scores, rounds, images or statistics.

### Installation & smoke check
1. Verify a recent Home Assistant backup before installing this prerelease.
2. Download exactly `v0.2.2b7` via Marketplace, restart Home Assistant, and clear/reload your Lovelace browser cache if the new custom element is not immediately recognized.
3. Create a **new**, separate manual card:
```yaml
type: custom:fbm-competition-card
title: Competición FBM
entity: sensor.competiciones
group_index: 0
```
4. Check classification → team → archived fixtures / players → player statistics → back to classification. The user must be an HA administrator to read archived rosters and player statistics.
5. Confirm that both automatic options remain enabled if previously selected. If the source has not yet archived a roster, the card correctly shows it as unavailable.

### Rollback
Reinstall `v0.2.2b6` and restart Home Assistant. Remove only the **new** `custom:fbm-competition-card` card from your dashboard if rolling back; existing FBM cards remain supported.

## Español
### Nueva tarjeta para seguir una competición
- Añadida `custom:fbm-competition-card`, independiente de las tarjetas actuales `custom:fbm-card` (búsqueda y equipo fijo).
- Clasificación de liga desde `sensor.competiciones`. Pulsando un equipo se abre su ficha con resultados, plantilla y estadísticas archivadas.
- Partidos agrupados por jornada cuando existe el número oficial, o vista de la fase completa. Pulsar un jugador muestra estadísticas globales y por partido solo cuando constan en el archivo.
- Las tarjetas fijas dan prioridad a clasificación/calendario de SQLite para evitar consultas duplicadas. La tarjeta de búsqueda detecta la sesión al abrirse. La pestaña Jugadores carga la plantilla automáticamente si no existe o lleva más de 15 minutos sin actualizar. Los botones de diagnóstico técnico quedan ocultos por defecto.
- Los escudos se muestran únicamente si la FBM proporciona una URL HTTPS completa y verificada de un dominio oficial admitido. Si no existe imagen válida, se muestra 🏀. **No está garantizado disponer de los escudos de todos los equipos.**
- La consulta de plantillas y estadísticas archivadas requiere cuenta administradora de HA, comprueba pertenencia a competición seguida y lee exclusivamente el archivo SQLite. Abrir un equipo en esta nueva tarjeta no lanza consultas extra a FBM.
- Se conservan las opciones de sincronización automática de b6. Sin cambios intencionados de esquema SQLite y sin inventar fechas, jornadas, fotos ni estadísticas.

### Instalación y prueba visual
1. Confirma una copia de seguridad reciente antes de instalar la beta.
2. Descarga `v0.2.2b7` desde Marketplace, reinicia HA y recarga/limpia la caché de Lovelace si no reconoce el nuevo tipo de tarjeta.
3. Añade una **tarjeta manual nueva e independiente**:
```yaml
type: custom:fbm-competition-card
title: Competición FBM
entity: sensor.competiciones
group_index: 0
```
4. Comprueba clasificación → equipo → partidos / jugadores → estadísticas → volver. Las plantillas y estadísticas archivadas requieren usuario administrador de HA.
5. Verifica que ambas actualizaciones automáticas siguen activas si ya lo estaban. Es correcto mostrar «sin plantilla archivada» si todavía no existe.

### Reversión
Vuelve a instalar `v0.2.2b6`, reinicia HA y elimina únicamente la tarjeta nueva `custom:fbm-competition-card` del panel en caso de revertir. Las tarjetas anteriores seguirán siendo compatibles.
