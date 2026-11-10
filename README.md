# FBM Card — Madrid Basketball Federation

Unofficial Home Assistant integration and Lovelace card using FBM/Afición FBM data. **Current candidate: 0.2.0b15 (beta).** It is not an official FBM product.

## Features
- Search FBM teams and save multiple favorites.
- Independent search and fixed-team cards; each fixed card retains its own team.
- Official group standings, rounds and match schedules (including date in the round selector), fixtures and available results.
- Team rosters and the sporting statistics returned by FBM. Missing statistics are hidden instead of guessed.
- Official team crests in headers and fixture lists, when a valid image reference is available.
- Small player photographs only when the official field contains a recognized and size-limited PNG, JPEG or WebP image. **Player photographs are not yet visually verified against the live FBM service.**

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

## 0.2.0b15 changes
- APK 5.0.42 bytecode analysis confirms the official image base at `imagenes.ashx`, the image-rendering path `?tipo=jugador&id=`, and the `JugadorEquipoDto.Foto` field flowing into that renderer.
- For the observed hex-encoded UTF-16LE opaque `Foto` reference, the backend now builds a fixed-host official player-image URL; it never invents an image payload or uses player name/ID as substitute.
- Only strictly bounded, format-validated references from FBM are accepted; the card allows only that exact official image endpoint or validated inline images, with error fallback.
- **The URL construction is supported by APK code; successful live image retrieval still needs visual confirmation in Home Assistant.**
- Supports `hex(UTF-16LE(Base64(image)))` **only when the decoded bytes have a verified PNG/JPEG/WebP signature and respect the size limit**; opaque IDs remain hidden.
- The player-photo diagnostic adds `utf16le_inner_magic` with a fixed category (png/jpeg/webp/other/invalid_base64), without exposing player images or identifiers.
- Real FBM player photos have **not yet been visually verified**; this is a controlled compatibility candidate.
- Extends the player-photo diagnostic to classify hexadecimal UTF-16LE text as URL, embedded URL, relative path, inline image, encoded reference or opaque text. Shows only permitted metadata and a boolean for the official FBM host. No raw photos or identifiers.
- Adds an explicit **Diagnosticar fotos** action in the Players tab to inspect safe, allowlisted photo-format metadata from the official backend; no photo, URL, identifier or secret is displayed.
- Accept **hex-encoded image bytes** in the same strict PNG/JPEG/WebP validator already used for Base64 images; reject encoded URLs and opaque identifiers.
- Add regression tests for valid image signatures and invalid references.
- No changes to crests, fixtures, standings, favorites or session behavior.
- The hex image compatibility was introduced in 0.2.0b11 and did not resolve the observed missing player photographs. This diagnostic release is **not confirmation** that live FBM player photos use this format. If photos still do not display, the image reference must be diagnosed using metadata-only tools, not guessed endpoints.

## Security and development
Photos and account/device secrets must not be posted in issues or diagnostics. The integration handles the guest identity separately and does not create a new identity per card. See [GitHub Actions](https://github.com/sergey08/Fbm-card/actions) for automated tests. Functional validation in Home Assistant is separate from automated CI. The project is experimental, unofficial and unaffiliated with FBM.

---

# FBM Card — Federación de Baloncesto de Madrid

Integración no oficial de Home Assistant y tarjeta Lovelace que consulta datos de FBM/Afición FBM. **Versión candidata actual: 0.2.0b15 (beta).** No es un producto oficial de la Federación.

## Funciones
- Búsqueda de equipos FBM y varios favoritos.
- Tarjetas independientes de búsqueda y equipos fijos, con selección de equipo propia.
- Clasificaciones, jornadas con fecha en el selector, enfrentamientos y resultados oficiales disponibles.
- Plantillas y estadísticas deportivas devueltas por FBM; se ocultan las estadísticas que no existan, sin inventarlas.
- Escudos oficiales en cabeceras y partidos cuando exista una referencia de imagen válida.
- Fotografías pequeñas de jugadores únicamente cuando el campo oficial contenga imágenes PNG, JPEG o WebP reconocidas y con tamaño limitado. **Las fotos de jugadores aún no están validadas visualmente con respuestas reales de FBM.**

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

## Cambios 0.2.0b15
- El análisis del código DEX de la APK 5.0.42 confirma el servicio oficial `imagenes.ashx`, la construcción `?tipo=jugador&id=` y el paso del campo `JugadorEquipoDto.Foto` al componente de imágenes.
- Para la referencia opaca `Foto` con formato hexadecimal UTF-16LE observado, el backend construye una URL del servidor oficial con dominio fijo; nunca inventa contenido de imagen ni sustituye la referencia por el nombre o ID del jugador.
- Solo acepta referencias estrictamente limitadas y verificadas estructuralmente; la tarjeta admite únicamente este endpoint oficial o imágenes inline validadas y oculta miniaturas fallidas.
- **La construcción está respaldada por el código de la APK, pero la visualización real en Home Assistant todavía requiere confirmación.**
- Admite `hex(UTF-16LE(Base64(imagen)))` **solo cuando los bytes decodificados tienen cabecera PNG/JPEG/WebP verificada y cumplen el límite de tamaño**; los identificadores opacos no se muestran.
- El diagnóstico de fotos incorpora `utf16le_inner_magic` con una categoría fija (png/jpeg/webp/other/invalid_base64), sin revelar imágenes ni identificadores.
- Las fotografías reales de FBM **aún no se han validado visualmente**; se trata de una candidata de compatibilidad controlada.
- Amplía el diagnóstico de fotos para clasificar el texto hexadecimal UTF-16LE como URL, URL incrustada, ruta, imagen inline, referencia codificada u otro texto. Solo muestra metadatos permitidos y un indicador del dominio oficial FBM. Nunca devuelve fotos ni identificadores.
- Nueva acción **Diagnosticar fotos** en la pestaña Jugadores: muestra únicamente metadatos seguros y autorizados del formato de imagen recibido de FBM, nunca fotos, URLs, identificadores ni secretos.
- Se admiten **bytes de imagen codificados en hexadecimal** usando el mismo validador estricto PNG/JPEG/WebP que ya admitía Base64. Se rechazan URLs e identificadores opacos codificados.
- Nuevas pruebas de regresión con cabeceras de imagen válidas y referencias inválidas.
- Sin cambios en escudos, partidos, clasificaciones, favoritos ni sesiones.
- La compatibilidad hexadecimal se incorporó en 0.2.0b11, pero no resolvió las fotografías ausentes observadas. Esta versión de diagnóstico **no confirma** de que las fotos reales de FBM empleen este formato. Si continúan ausentes, hay que diagnosticar el formato de la referencia mediante metadatos, sin inventar endpoints.

## Seguridad y desarrollo
No publiques fotos ni secretos de la cuenta/dispositivo en incidencias ni diagnósticos. La integración gestiona una sola identidad invitada compartida, sin crear otra por tarjeta. Consulta las [pruebas de GitHub Actions](https://github.com/sergey08/Fbm-card/actions). La validación funcional real en Home Assistant es distinta de las pruebas automáticas. Proyecto experimental, no oficial y sin afiliación con FBM.
