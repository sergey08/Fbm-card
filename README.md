# FBM Card — Madrid Basketball Federation

Unofficial Home Assistant integration and Lovelace card using FBM/Afición FBM data. **Current stable version: 0.2.0.** It is not an official FBM product.

## Features
- Search FBM teams and save multiple favorites.
- Independent search and fixed-team cards; each fixed card retains its own team.
- Official group standings, rounds and match schedules (including date in the round selector), fixtures and available results.
- Team rosters and the sporting statistics returned by FBM. Missing statistics are hidden instead of guessed.
- Official team crests in headers and fixture lists, when a valid image reference is available.
- Small player photographs retrieved from the APK-verified official FBM image endpoint or validated inline images; real photographs were visually verified on 0.2.0b15.

## Installing or updating
Install **FBM para Home Assistant** from Home Assistant Marketplace (formerly HACS), then restart Home Assistant if requested. The integration registers the `/fbm_static/fbm-card.js` Lovelace resource; do not register a duplicate JavaScript resource. Refresh the browser if the card is cached. Keep your existing FBM guest identity and configuration; do not re-register the device after updating.

### Team search card
```yaml
type: custom:fbm-card
modo_experimental: true
tipo_tarjeta: busqueda
title: Search FBM teams
id_tarjeta: buscador_fbm
```
Select a team and use the card's **copy fixed team configuration** action to create independent cards. The generated YAML contains the official identifiers and avoids creating additional guest identities.

### Fixed team card
```yaml
type: custom:fbm-card
modo_experimental: true
tipo_tarjeta: equipo
title: My team
id_tarjeta: mi_equipo
equipo_fijo:
  id: "OFFICIAL_TEAM_ID"
  nombre: "Official team name"
  club: "Club"
  categoria: "Category"
  temporada: "26/27"
```
Replace the sample fields using the configuration copied by the search card. Teams saved only in browser storage may not sync between devices.

## Version 0.2.0 — first stable release
- Includes team search, favorites, independent fixed-team cards, group standings, match schedules, rosters, statistics and team crests.
- Player photographs use the official image endpoint verified against Afición FBM 5.0.42 APK bytecode. **Real photographs were visually verified in Home Assistant on 0.2.0b15 across multiple teams.**
- Preserves the existing guest identity and card configuration; no device re-registration is required.
- Missing statistics are hidden rather than invented.
- Future updates will use stable GitHub/Marketplace releases; development changes continue to be validated before merging.

## Security and development
Photos and account/device secrets must not be posted in issues or diagnostics. The integration handles the guest identity separately and does not create a new identity per card. See [GitHub Actions](https://github.com/sergey08/Fbm-card/actions) for automated tests. Functional validation in Home Assistant is separate from automated CI. The project is experimental, unofficial and unaffiliated with FBM.

---

# FBM Card — Federación de Baloncesto de Madrid

Integración no oficial de Home Assistant y tarjeta Lovelace que consulta datos de FBM/Afición FBM. **Versión estable actual: 0.2.0.** No es un producto oficial de la Federación.

## Funciones
- Búsqueda de equipos FBM y varios favoritos.
- Tarjetas independientes de búsqueda y equipos fijos, con selección de equipo propia.
- Clasificaciones, jornadas con fecha en el selector, enfrentamientos y resultados oficiales disponibles.
- Plantillas y estadísticas deportivas devueltas por FBM; se ocultan las estadísticas que no existan, sin inventarlas.
- Escudos oficiales en cabeceras y partidos cuando exista una referencia de imagen válida.
- Fotografías pequeñas de jugadores obtenidas del servicio oficial de imágenes identificado en la APK o de imágenes inline validadas; las fotografías reales se comprobaron visualmente en 0.2.0b15.

## Instalación y actualización
Instala **FBM para Home Assistant** desde Marketplace (antes HACS) y reinicia Home Assistant si lo solicita. La integración registra el recurso Lovelace `/fbm_static/fbm-card.js`; no añadas otro recurso JavaScript duplicado. Recarga el navegador si mantiene la tarjeta anterior en caché. Conserva tu identidad invitada y configuración FBM: no vuelvas a registrar el dispositivo después de actualizar.

### Tarjeta de búsqueda
```yaml
type: custom:fbm-card
modo_experimental: true
tipo_tarjeta: busqueda
title: Buscar equipos FBM
id_tarjeta: buscador_fbm
```
Selecciona un equipo y utiliza la opción **copiar configuración de tarjeta fija** para crear tarjetas independientes. El YAML generado contiene los identificadores oficiales y no crea identidades invitadas adicionales.

### Tarjeta de equipo fijo
```yaml
type: custom:fbm-card
modo_experimental: true
tipo_tarjeta: equipo
title: Mi equipo
id_tarjeta: mi_equipo
equipo_fijo:
  id: "ID_OFICIAL_DEL_EQUIPO"
  nombre: "Nombre oficial"
  club: "Club"
  categoria: "Categoría"
  temporada: "26/27"
```
Sustituye los valores del ejemplo con la configuración copiada desde el buscador. Las selecciones guardadas solo en el navegador pueden no sincronizarse entre dispositivos.

## Version 0.2.0 — primera versión estable
- Incluye la búsqueda, favoritos, equipos fijos independientes, clasificación, calendario de partidos, plantillas, estadísticas y escudos.
- Las fotografías de jugadores usan la ruta oficial verificada mediante análisis de la APK Afición FBM 5.0.42. **Visualización confirmada en Home Assistant con varios equipos en la beta 0.2.0b15.**
- Mantiene la identidad invitada existente y las tarjetas configuradas; no hace falta volver a registrar dispositivos.
- Las estadísticas que FBM no proporciona se ocultan, sin inventar valores.
- Las actualizaciones futuras se distribuirán mediante releases estables de GitHub/Marketplace; los cambios de desarrollo seguirán probándose antes de fusionar.

## Seguridad y desarrollo
No publiques fotos ni secretos de la cuenta/dispositivo en incidencias ni diagnósticos. La integración gestiona una sola identidad invitada compartida, sin crear otra por tarjeta. Consulta las [pruebas de GitHub Actions](https://github.com/sergey08/Fbm-card/actions). La validación funcional real en Home Assistant es distinta de las pruebas automáticas. Proyecto experimental, no oficial y sin afiliación con FBM.
