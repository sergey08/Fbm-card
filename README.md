# FBM Card — Federación de Baloncesto de Madrid

Integración no oficial para **Home Assistant** que incluye la tarjeta Lovelace `custom:fbm-card`.

> **Estado: candidata a v0.1 en la rama `dev`, todavía sin publicación estable.**
> En Home Assistant real se han validado registro invitado, conexión, búsqueda de equipos y clasificación mediante la aplicación oficial Afición FBM. La interfaz se ha probado visualmente. **Los horarios y partidos quedan fuera del alcance inicial** y se estudiarán más adelante.

## Qué incluye la primera versión

- Búsqueda de equipos de la FBM, con su club, categoría y temporada.
- Selección de equipo y consulta bajo demanda de la **clasificación oficial** del grupo.
- Registro de **una identidad local independiente** como dispositivo invitado y posterior conexión explícita. No hay necesidad de facilitar una cuenta personal de FBM, pero **sí hay un registro de dispositivo ante el servicio oficial**.
- Interfaz Lovelace que evita registros y peticiones automáticas al abrir la tarjeta.
- Una instalación que contiene la **integración Python y el JavaScript de la tarjeta**.

**No disponible en v0.1:** consulta de horarios, calendario y partidos. El diagnóstico queda recogido en [incidencia #3](https://github.com/sergey08/Fbm-card/issues/3).

## Instalación prevista con Marketplace

La distribución final será una única **integración** que registre automáticamente el recurso de la tarjeta. **No hay una versión estable publicada todavía:** las instrucciones siguientes se aplicarán cuando exista una release validada.

1. En Marketplace, busca **FBM para Home Assistant** e instala la integración, una vez disponible.
2. Reinicia Home Assistant según indique Marketplace.
3. Ve a **Configuración → Dispositivos y servicios → Añadir integración** y selecciona *Federación de Baloncesto de Madrid*.
4. Añade una tarjeta manual al panel deseado:

```yaml
type: custom:fbm-card
title: Mis equipos FBM
modo_experimental: true
id_tarjeta: mis_equipos
```

5. En la tarjeta pulsa **Comprobar estado**. Si todavía no hay identidad, créala **una sola vez**. Registra el dispositivo en FBM explícitamente, conecta y busca el equipo. **Nunca repitas el registro ante un fallo incierto**: utiliza la recuperación guiada.
6. Selecciona equipo, categoría y temporada; pulsa **Consultar clasificación del grupo actual**. La consulta requiere conexión vigente.

No añadas manualmente otro recurso `fbm-card.js` si la integración ya ha registrado `/fbm_static/fbm-card.js`: dos versiones del mismo elemento personalizado pueden interferir en el navegador.

## Dos tipos de tarjeta (DEV)

**Buscador de equipos**: consulta y selecciona equipos en el servicio oficial FBM, con categoría y temporada. No crea una identidad por abrir la tarjeta.

```yaml
type: custom:fbm-card
modo_experimental: true
tipo_tarjeta: busqueda
title: Buscar equipos FBM
id_tarjeta: buscador_fbm
```

Después de elegir un equipo, usa **Copiar configuración de tarjeta fija**, crea otra tarjeta manual y pega el YAML generado. Así el equipo permanece en la configuración del dashboard, incluso desde otro navegador o dispositivo con permiso para ver ese panel.

**Equipo fijo**: también se puede añadir una tarjeta vacía de este tipo; busca el equipo y pulsa «Fijar este equipo en la tarjeta». Si lo haces así, la selección se guarda solo en el navegador del usuario. Para persistencia en Home Assistant entre dispositivos, utiliza el YAML generado por el buscador:

```yaml
type: custom:fbm-card
modo_experimental: true
tipo_tarjeta: equipo
title: Mi equipo
id_tarjeta: mi_equipo_fijo
equipo_fijo:
  id: "ID_OFICIAL_DEL_EQUIPO"
  nombre: "Nombre oficial"
  club: "Club"
  categoria: "Categoría"
  temporada: "26/27"
```

Los campos del ejemplo son marcadores: **no funcionan hasta sustituirlos por los datos reales del equipo obtenidos en la búsqueda**. El botón de copia genera esos valores automáticamente y no incluye credenciales privadas.

Al abrir la tarjeta fija, se comprueba el estado de la integración y se consulta la clasificación **si la sesión de invitado continúa vigente**. Tras un reinicio o caducidad, pulsa **Conectar** para recuperar la sesión existente; no vuelvas a crear ni registrar otra identidad. El calendario y los horarios siguen fuera del alcance v0.1.

## Seguridad y límites

El registro se envía exclusivamente a los endpoints oficiales de Afición FBM; la identidad del dispositivo se guarda en almacenamiento privado de Home Assistant. La clave de sesión se mantiene en memoria; no se incluyen credenciales en mensajes, logs, URL o preferencias del navegador. La tarjeta no crea identidades ni se registra automáticamente. Las consultas se realizan cuando el usuario pulsa los botones y aplican caché de corta duración.

La selección del equipo en el modo experimental se guarda localmente por usuario, tarjeta e integración, **sin sincronización entre dispositivos**. El flujo permite escoger equipos entre categorías y temporadas; **no hay todavía un catálogo guiado Competición → Categoría → Club → Equipo ni un gestor completo de múltiples favoritos en el modo experimental**.

## Validación y desarrollo

- `main`: rama destinada a la versión publicada; **no mezclar desarrollo sin verificar**.
- `dev`: rama activa de desarrollo y pruebas.
- [GitHub Actions](https://github.com/sergey08/Fbm-card/actions): valida sintaxis, pruebas JavaScript y Python, empaquetado y genera un ZIP experimental temporal de la integración.
- La prueba funcional de la v0.1 se ha hecho en HA Core 2026.11.0 con una identidad de invitado, búsquedas reales y clasificaciones oficiales; ello no garantiza el comportamiento de todas las categorías o instalaciones.

**Proyecto comunitario no oficial, sin afiliación con la Federación de Baloncesto de Madrid.**
