# FBM Card 0.2.2b11 (Beta)

## English

- Add **FBM Card** from the Home Assistant visual card picker to search for teams. Select a result or favorite and open its matches, standings, or players. Matches include phase and matchday views. Favorites and the option to copy a fixed-team configuration remain available.
- Fixed-team cards load standings automatically, retain team crests and available player photos, and place **Change team** at the bottom. Give each fixed card a distinct `id_tarjeta` to enable independent changes. Cards with an embedded team and a card ID can override that team in the current browser. Cards without an ID keep their configured team.
- Competition cards show current, last completed and upcoming matchdays when supported by archived fixtures. Undated or explicitly postponed fixtures do not determine the calendar window. Team names and verified crests open the team detail, with matches, standings, archived players and available statistics. The back button returns to the competition. The archived detail requires a Home Assistant administrator. Archived rosters omit player photos.
- Search uses local archived standings when available. Competition navigation reads the local archive, with no added FBM API requests. The automatic player and group intervals remain two and four hours, respectively.

### Install and verify

1. In HACS, open **FBM para Home Assistant**, choose **Redownload**, select `v0.2.2b11` and restart Home Assistant.
2. In the dashboard resources, if the browser still serves the previous JavaScript, update the existing module to `/fbm_static/fbm-card.js?v=0.2.2b11` and reload the dashboard.
3. Add **FBM Card** through the visual picker. Check a favorite, two fixed cards with different IDs, the competition drill-down and the return button. Verify `sensor.competiciones.attributes.automatic_refresh` after each enabled interval. Keep the existing FBM configuration and device identity.
4. To roll back, redownload `v0.2.2b10`, restart Home Assistant and set the existing resource query to `?v=0.2.2b10` if needed.

## Español

- Añade **FBM Card** desde el selector visual de Home Assistant para buscar equipos. Selecciona un resultado o un favorito y abre sus partidos, clasificación o jugadores. Partidos incluye vistas de fase y jornada. Se conservan los favoritos y la opción de copiar la configuración de un equipo fijo.
- Las tarjetas de equipo fijo cargan la clasificación automáticamente, conservan los escudos y las fotos disponibles, y sitúan **Cambiar equipo** al final. Asigna un `id_tarjeta` distinto a cada tarjeta fija para cambiar equipos de forma independiente. Las tarjetas con equipo configurado y un identificador pueden cambiar de equipo en el navegador actual. Las tarjetas sin identificador conservan el equipo configurado.
- Las tarjetas de competición muestran la jornada actual, la última completada y la próxima cuando los partidos archivados permiten identificarlas. Los partidos sin fecha o expresamente aplazados quedan fuera del cálculo de la ventana de juego. El nombre y el escudo oficial del equipo abren sus partidos, clasificación, jugadores archivados y estadísticas disponibles. El botón de regreso vuelve a la competición. El detalle archivado requiere una cuenta administradora de Home Assistant. Las plantillas archivadas omiten las fotos de jugadores.
- El buscador reutiliza la clasificación archivada cuando está disponible. La navegación de competición lee el archivo local sin añadir peticiones a la API de FBM. Los intervalos automáticos siguen siendo de dos horas para jugadores y cuatro horas para grupos.

### Instalación y verificación

1. En HACS, abre **FBM para Home Assistant**, elige **Descargar de nuevo**, selecciona `v0.2.2b11` y reinicia Home Assistant.
2. Si el navegador conserva el JavaScript anterior, edita el recurso existente del panel a `/fbm_static/fbm-card.js?v=0.2.2b11` y vuelve a cargar el panel.
3. Añade **FBM Card** con el selector visual. Comprueba un favorito, dos tarjetas fijas con IDs distintos, el detalle de competición y el botón de regreso. Comprueba `sensor.competiciones.attributes.automatic_refresh` después del intervalo de cada proceso activo. Conserva la configuración y la identidad de FBM.
4. Para volver a b10, descarga `v0.2.2b10`, reinicia Home Assistant y cambia la consulta del recurso existente a `?v=0.2.2b10` si hace falta.
