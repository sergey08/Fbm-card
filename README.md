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

## Favoritos y tarjetas independientes (DEV)

El buscador permite seleccionar un equipo de la lista oficial de FBM y pulsar **☆ Añadir a favoritos**. Se pueden guardar **varios equipos**, volver a elegirlos en el selector «Mis equipos favoritos» y quitarlos con «★ Quitar de favoritos». Cada favorito conserva el nombre oficial, club, categoría, temporada e ID del equipo, pero **nunca** almacena el UID, la clave del dispositivo o la sesión de FBM.

El botón **Copiar tarjeta independiente de este equipo** produce una configuración YAML con `tipo_tarjeta: equipo` y `equipo_fijo`. Crea una tarjeta manual nueva en el panel de Home Assistant y pega esa configuración. Repite el procedimiento con otros favoritos: las tarjetas quedan **independientes entre sí**, cada una con su clasificación, sin alterar el buscador ni las otras tarjetas. La integración y la identidad invitada son compartidas; **no debe registrarse otro dispositivo por tarjeta**.

Los favoritos del buscador se guardan localmente **por usuario de Home Assistant, navegador y entrada FBM** (sin sincronización entre navegadores). Las tarjetas fijas creadas mediante YAML se guardan en la configuración del dashboard y, por tanto, mantienen su equipo al abrir el mismo panel desde otro dispositivo. El botón «Fijar este equipo en la tarjeta» de una tarjeta fija vacía conserva la selección únicamente en el almacenamiento de ese navegador; para una selección portátil usa la opción de copiar YAML.

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

## Pestañas de equipo — desarrollo posterior a v0.1

Las tarjetas con `tipo_tarjeta: equipo` muestran una cabecera independiente con nombre, categoría, club y temporada, además de tres pestañas: **Partidos**, **Clasificación** y **Jugadores**.

- **Clasificación:** sección ya validada con datos reales de FBM. Permanece como pestaña inicial y puede actualizarse expresamente.
- **Partidos / Fases:** permite consultar las fases y rondas oficiales disponibles para el equipo desde la sesión invitada. Las consultas de calendario y los enfrentamientos por jornada todavía NO están validados; esta pestaña no muestra partidos inventados.
- **Partidos / Jornadas:** interfaz preparada para mostrar encuentros de **todo el grupo**, no solo los del equipo fijado. Se mantiene un aviso de «pendiente» mientras la consulta oficial `horariosJornadas` falle.
- **Jugadores:** pestaña preparada; todavía sin lista de jugadores porque la integración no dispone de un endpoint oficial de plantilla validado. Evitar recopilar información personal adicional o mostrar datos no confirmados, especialmente de menores.
- **Escudo:** opcional `logo_equipo: https://...` solo con una URL HTTPS alojada en un dominio de FBM admitido por el cliente; en ausencia de un escudo oficial verificado se muestra un icono neutro.

Estas pestañas son **experimentales**. No se ha publicado una versión estable que incluya partidas, plantillas o escudos automáticos y no se debe anunciar esas funciones como disponibles hasta comprobar la fuente de datos y su respuesta en Home Assistant.

## Seguridad y límites

El registro se envía exclusivamente a los endpoints oficiales de Afición FBM; la identidad del dispositivo se guarda en almacenamiento privado de Home Assistant. La clave de sesión se mantiene en memoria; no se incluyen credenciales en mensajes, logs, URL o preferencias del navegador. La tarjeta no crea identidades ni se registra automáticamente. Las consultas se realizan cuando el usuario pulsa los botones y aplican caché de corta duración.

La selección del equipo en el modo experimental se guarda localmente por usuario, tarjeta e integración, **sin sincronización entre dispositivos**. El flujo permite escoger equipos entre categorías y temporadas; **no hay todavía un catálogo guiado Competición → Categoría → Club → Equipo ni un gestor completo de múltiples favoritos en el modo experimental**.

## Validación y desarrollo

- `main`: rama destinada a la versión publicada; **no mezclar desarrollo sin verificar**.
- `dev`: rama activa de desarrollo y pruebas.
- [GitHub Actions](https://github.com/sergey08/Fbm-card/actions): valida sintaxis, pruebas JavaScript y Python, empaquetado y genera un ZIP experimental temporal de la integración.
- La prueba funcional de la v0.1 se ha hecho en HA Core 2026.11.0 con una identidad de invitado, búsquedas reales y clasificaciones oficiales; ello no garantiza el comportamiento de todas las categorías o instalaciones.

**Proyecto comunitario no oficial, sin afiliación con la Federación de Baloncesto de Madrid.**
