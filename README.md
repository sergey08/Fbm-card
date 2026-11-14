# FBM Card — Baloncesto madrileño en Home Assistant

![Logo de FBM Card](assets/fbm-card-logo.svg)

> **Proyecto comunitario no oficial.** No está afiliado, respaldado ni mantenido por la Federación de Baloncesto de Madrid (FBM).

**Versión estable:** v0.2.3 (validada en Home Assistant).

FBM Card combina una integración de Home Assistant y tarjetas Lovelace para consultar datos públicos de baloncesto FBM: equipos, competiciones, calendarios, resultados, clasificaciones, plantillas y estadísticas disponibles de jugadores. Está pensada para seguir varias competiciones sin descargar repetidamente datos que no han cambiado.

## Funciones

- Buscar equipos FBM y guardar favoritos; tarjetas independientes de búsqueda, equipo y competición.
- Seguir varios grupos y consultar clasificaciones, jornadas, enfrentamientos y resultados oficiales.
- Mostrar escudos de equipos y fotografías de jugadores cuando existan imágenes oficiales verificadas.
- Configurar los ajustes compatibles mediante un editor visual; YAML para opciones avanzadas.
- Archivar datos localmente y actualizar grupos y jugadores de manera incremental.
- Consultar cobertura por grupo: equipos, plantillas archivadas, jugadores con estadísticas completas, pendientes y porcentaje.
- No inventar marcadores, estadísticas, fotografías ni datos ausentes. La disponibilidad depende de FBM.

## Instalación

1. Instala **FBM para Home Assistant** mediante Marketplace/HACS; añade este repositorio si es necesario.
2. Configura la integración FBM en **Ajustes → Dispositivos y servicios** y sigue los equipos o competiciones deseados.
3. Reinicia Home Assistant si se solicita. La integración registra automáticamente `/fbm_static/fbm-card.js`: **no dupliques el recurso Lovelace**.
4. Añade una **FBM Card** desde el selector de tarjetas y utiliza el editor visual o YAML.
5. Recarga el navegador si sigue mostrando una tarjeta antigua en caché.

**Actualizaciones:** conserva la identidad invitada y la configuración existente. No elimines ni vuelvas a añadir la integración, ni registres otra vez el dispositivo, solo por actualizar la tarjeta.

## Tarjetas y ejemplos de configuración

**Tarjeta de búsqueda** — encuentra un equipo y copia sus identificadores oficiales:

```yaml
type: custom:fbm-card
modo_experimental: true
tipo_tarjeta: busqueda
title: Buscar equipos FBM
id_tarjeta: buscador_fbm
```

**Tarjeta de equipo fijo** — utiliza los valores oficiales copiados del buscador:

```yaml
type: custom:fbm-card
modo_experimental: true
tipo_tarjeta: equipo
title: Mi equipo
id_tarjeta: mi_equipo
equipo_fijo:
  id: "ID_OFICIAL_DEL_EQUIPO"
  nombre: "Nombre oficial del equipo"
  club: "Club"
  categoria: "Categoría"
  temporada: "26/27"
```

Es preferible configurar la tarjeta de competición desde el editor visual, seleccionando una competición seguida. Las opciones disponibles dependen de la versión instalada. No inventes identificadores de competición.

## Sincronización y cobertura

FBM Card guarda los últimos datos archivados y permite actualizar estadísticas de jugadores en lotes limitados. Omite registros completos cuando el número de partidos archivados coincide con las apariciones oficiales y existen puntos por partido. Los jugadores sin apariciones no necesitan consultas de estadísticas de partidos.

La entidad `sensor.competiciones` ofrece el atributo `coverage` con datos por grupo y totales (`teams`, `rosters`, `players`, `complete`, `pending`, `missing_rosters`, `coverage_percent`). El porcentaje mide la **cobertura de las apariciones registradas y archivadas hasta ese momento**, no garantiza que FBM haya publicado estadísticas futuras.

**Validación real (14/11/2026):** cinco grupos seguidos, 30 equipos, 30 plantillas y 321/321 jugadores evaluables completos (100 %) tras una recuperación incremental explícita. Es una fotografía de una instalación concreta, **no un resultado garantizado para todos los usuarios**. La actualización automática tras nuevos partidos sigue pendiente de comprobación.

## Versiones

- **v0.2.3 (estable):** incorpora el icono PNG de FBM Card en la integración de Home Assistant, sin modificar la sincronización ni las tarjetas.

- **v0.2.2 (estable):** sincronización incremental de competiciones y estadísticas de jugadores, diagnóstico de cobertura, tarjetas y editor visual, README en español y logo propio. La validación automática tras la próxima jornada sigue pendiente.
- **v0.2.1 (estable):** mantenimiento de numeración y actualización desde Marketplace.
- **v0.2.0 (estable):** búsqueda, favoritos, clasificaciones, calendarios, plantillas, estadísticas e imágenes oficiales verificadas.

Consulta las [pruebas de GitHub Actions](https://github.com/sergey08/Fbm-card/actions). Las pruebas automáticas no sustituyen la validación funcional en Home Assistant.

## Privacidad, limitaciones y soporte

Este proyecto usa datos deportivos públicos y una identidad invitada FBM compartida. No publiques tokens, datos de registro del dispositivo, información personal ni fotografías de jugadores en incidencias públicas. La disponibilidad de datos, rutas e imágenes oficiales puede cambiar. Para comunicar errores, abre una [incidencia en GitHub](https://github.com/sergey08/Fbm-card/issues) indicando versión de Home Assistant, versión de FBM Card, registros anonimizados y pasos para reproducir el problema.
