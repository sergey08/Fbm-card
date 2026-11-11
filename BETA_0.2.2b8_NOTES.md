# FBM Card 0.2.2b8 — Consistent competition card design / Diseño unificado

## English
### What's new in b8
- Redesigns the **Competition Card** to match the existing FBM search and fixed-team cards. Consistent title typography, padding, blue active tabs, theme-aware backgrounds, table headers, alternating rows, player blocks, and responsive mobile layout.
- Classification is now displayed inside a rounded, horizontally scrollable table on narrow screens; no content should be clipped.
- The team detail has the same prominent 52px team-crest header as the original FBM fixed-team card, with a basketball fallback when no verified official crest URL exists.
- Matches, rounds, roster, and per-game statistics introduced in b7 remain available; no new FBM network calls are added.
- Does **not** change existing `custom:fbm-card` appearance, options, stored preferences, or the SQLite archive.

### Install and test
1. Keep your existing dashboard cards and take/verify a recent Home Assistant backup.
2. In Marketplace, select **Download again** and choose `v0.2.2b8`. Restart Home Assistant.
3. Confirm the Lovelace resource URL is `/fbm_static/fbm-card.js?v=0.2.2b8` (replace the existing resource, **never add a duplicate**), then reload the mobile application. This is required to avoid stale JavaScript caching.
4. Reuse the existing card:
```yaml
type: custom:fbm-competition-card
title: Competición FBM
entity: sensor.competiciones
group_index: 0
```
5. Compare the new Competition Card with the Search and Fixed Team cards in mobile and desktop views. Check standings → team → fixtures and players → player stats → back.

### Rollback
Reinstall `v0.2.2b7`, restart Home Assistant, restore the resource query to `?v=0.2.2b7`, and reload the browser. Existing cards and stored competition data are preserved.

## Español
### Novedades de b8
- Rediseño de la **Tarjeta de competiciones** para que mantenga la misma estética que las tarjetas FBM de búsqueda y equipo fijo: títulos, márgenes, pestañas azules, colores del tema, cabeceras de clasificación, filas alternas, fichas de jugadores y diseño adaptable a móvil.
- Clasificación dentro de una tabla con esquinas redondeadas y desplazamiento horizontal para evitar recortes en pantallas estrechas.
- Cabecera de equipo con escudo de 52 píxeles, igual que la tarjeta fija, y símbolo 🏀 cuando no exista una URL oficial de escudo validada.
- Se conservan las jornadas, los partidos, las plantillas y las estadísticas por partido incorporadas en b7. No se añaden peticiones nuevas a la FBM.
- **No se modifica** la apariencia de las tarjetas `custom:fbm-card` anteriores, las opciones de sincronización, las preferencias ni el archivo SQLite.

### Instalación y comprobación
1. Conserva las tarjetas existentes y confirma una copia de seguridad reciente de Home Assistant.
2. En Marketplace, selecciona **Descargar de nuevo** e instala `v0.2.2b8`. Reinicia Home Assistant.
3. Comprueba que el recurso Lovelace existente se actualiza a `/fbm_static/fbm-card.js?v=0.2.2b8` (editar el existente, **sin duplicarlo**) y vuelve a abrir la aplicación móvil. Así se evita la caché de JavaScript de la beta anterior.
4. Reutiliza la tarjeta que ya tienes creada:
```yaml
type: custom:fbm-competition-card
title: Competición FBM
entity: sensor.competiciones
group_index: 0
```
5. Compara su aspecto con las tarjetas de búsqueda y equipo fijo en móvil y ordenador. Comprueba clasificación → equipo → partidos y jugadores → estadísticas → volver.

### Reversión
Reinstala `v0.2.2b7`, reinicia HA, devuelve el recurso a `?v=0.2.2b7` y recarga Lovelace. No se eliminan datos ni tarjetas.
