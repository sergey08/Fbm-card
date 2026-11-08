# FBM Card

Tarjeta para Home Assistant con calendarios, resultados y clasificaciones de la Federación de Baloncesto de Madrid (FBM).

**Estado: desarrollo (rama dev). Sin conexión con datos oficiales todavía.**

## Primera beta prevista

- Equipo inicial: GRUPO EGIDO PINTOBASKET NEGRO.
- Próximos partidos, resultados y clasificación.
- Solo datos públicos, sin inicio de sesión.
- Favoritos locales en Home Assistant.

## Instalación desde GitHub

El repositorio contiene la estructura de una tarjeta personalizada compatible con la distribución por Marketplace/HACS. **Todavía no hay versión beta publicada.** No se debe instalar como estable.

## Prueba manual del componente DEV

Copiar `fbm-card.js` de `dev` a `/config/www/fbm-card.js`, registrar `/local/fbm-card.js` como recurso de tipo módulo y añadir:

```yaml
type: custom:fbm-card
title: FBM Card
equipo: GRUPO EGIDO PINTOBASKET NEGRO
```

Actualmente muestra un aviso de desarrollo; no presenta resultados inventados.

## Protocolo

- `main`: estable; `dev`: desarrollo y pruebas.
- Validar datos públicos y el paquete antes de publicar una beta.
- No fusionar ni publicar versión estable sin aprobación.

Proyecto no oficial, sin afiliación con la FBM.

## Formato de datos (contrato provisional DEV)

La tarjeta ya puede mostrar partidos y clasificación desde los atributos de una entidad de Home Assistant. Esta interfaz **no es todavía una integración con la FBM**; la entidad debe ser alimentada por una fuente oficial validada. No se incluyen resultados de ejemplo como datos reales.

```yaml
type: custom:fbm-card
title: FBM Card
equipo: GRUPO EGIDO PINTOBASKET NEGRO
entidad_datos: sensor.fbm_pintobasket
```

La entidad debe incluir un atributo `fbm` (o atributos de primer nivel) con esta estructura JSON:

```json
{
  "fuente": "FBM",
  "partidos": [
    {"local": "Equipo local", "visitante": "Equipo visitante", "fecha": "2026-11-14", "resultado": null}
  ],
  "clasificacion": [
    {"posicion": 1, "equipo": "Nombre del equipo", "jugados": 3, "puntos": 6}
  ],
  "actualizado": "2026-11-08"
}
```

Los valores anteriores describen únicamente el **formato**, no resultados verificados. Sin entidad o con datos incompletos, la tarjeta informa del problema. No consulta credenciales, ni inicia sesión, ni hace solicitudes HTTP directamente.

## Validación automatizada

El flujo `.github/workflows/validacion.yml` comprueba sintaxis, pruebas Node y manifiesto HACS al actualizar `dev` o abrir un PR. La existencia del flujo no implica que haya pasado: verificar su resultado en la pestaña Actions de GitHub.

## Enlace a la ficha oficial

Puede añadirse opcionalmente `url_oficial: https://www.fbm.es/...` para mostrar un enlace a la ficha pública del equipo o competición. Solo se aceptan enlaces HTTPS bajo `fbm.es`; no se asigna ninguna URL por defecto hasta confirmar la ficha exacta.

La web del club Pintobasket publica partidos y resultados, pero no se considera sustituto de la fuente oficial FBM para alimentar automáticamente la tarjeta.

## Selección de equipos por cada usuario (requisito obligatorio)

FBM Card es universal: **no estará limitada a Pintobasket**. Cada persona debe poder buscar y seleccionar equipos de cualquier competición de la Federación de Baloncesto de Madrid, mediante el recorrido **Competición → Categoría → Club → Equipo**. Debe poder seguir **varios equipos** y conservar sus favoritos de manera local, sin cuentas de Afición FBM. La selección y los favoritos serán independientes por usuario cuando Home Assistant permita identificar el usuario; no se deben compartir favoritos accidentalmente entre usuarios del mismo hogar.

**Fuente única:** FBM (web oficial o API oficial de Afición FBM, en modo invitado). Prohibido obtener calendarios, resultados, clasificación o catálogo de equipos desde clubes o fuentes de terceros.

**Estado actual:** este es un requisito de producto, **todavía no implementado**. El ejemplo de Pintobasket del README es solo un caso de prueba inicial y nunca debe fijarse como equipo obligatorio o predeterminado en la versión pública.

## Selector de varios equipos (implementado parcialmente en DEV)

La tarjeta permite configurar una lista de equipos y alternar entre ellos. La última selección se guarda **en el navegador/dispositivo**, con una clave que incluye el identificador del usuario de Home Assistant y `id_tarjeta`. No hay sincronización entre dispositivos ni catálogo automático de equipos todavía. Sin identidad de usuario no se guarda la preferencia.

```yaml
type: custom:fbm-card
title: Mis equipos FBM
id_tarjeta: mis_equipos
equipos:
  - nombre: Equipo A
    entidad_datos: sensor.fbm_equipo_a
  - nombre: Equipo B
    entidad_datos: sensor.fbm_equipo_b
```

**Los nombres y entidades anteriores son marcadores de configuración, no equipos reales ni fuentes de datos.** Para visualizar información, cada entidad debe estar alimentada exclusivamente por la FBM. El selector Competición → Categoría → Club → Equipo y la búsqueda del catálogo oficial siguen pendientes de implementar y validar contra la API pública FBM.

## Favoritos locales (DEV)

Ya se puede marcar o desmarcar como favorito cualquiera de los equipos configurados. Los favoritos aparecen primero en el selector, identificados con ★. Se almacenan en el navegador, separados por identificador de usuario de Home Assistant y por `id_tarjeta`. **No se sincronizan entre móviles u otros navegadores** y no permiten aún buscar equipos en el catálogo oficial: para eso sigue pendiente validar la API pública FBM. Sin identidad de usuario disponible no se muestra el botón para guardar favoritos.

## Restricción de procedencia de datos

El adaptador de datos debe obtener información **exclusivamente de endpoints oficiales de la FBM**. La tarjeta rechaza entidades cuyo atributo `fuente` no sea exactamente `FBM`. **Esta etiqueta es una comprobación de formato, no una prueba criptográfica de origen**: la garantía real depende del adaptador que consulte únicamente la FBM y de pruebas de integración contra sus endpoints oficiales. Está prohibido sustituirlos por fuentes de clubes o terceros.

## Descubrimiento de sensores FBM (DEV)

Cuando no hay equipos configurados, la tarjeta enumera hasta diez entidades `sensor.*` de Home Assistant con estructura de partidos/clasificación y `fuente: FBM`, para ayudar a configurar equipos. **No es aún el buscador oficial de clubes y equipos**: únicamente inspecciona sensores ya existentes, y una etiqueta declarada no certifica la procedencia. Sigue pendiente el adaptador que consulte exclusivamente FBM.
