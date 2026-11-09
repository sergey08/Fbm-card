> **Arquitectura DEV en transición.** Este repositorio está pasando de tarjeta independiente a **integración + tarjeta en una sola instalación**. Las pruebas de diagnóstico han recuperado equipos y horarios reales con una identidad independiente; el registro inicial, la compatibilidad y el flujo completo aún no se han validado en Home Assistant. El prototipo de tarjeta experimental y sus límites se describen en [identidad independiente](docs/identidad-independiente.md). El registro automático del recurso Lovelace tampoco se ha verificado en una instalación real. Las instrucciones anteriores de instalación manual son históricas y no describen aún la instalación final desde Marketplace. **No instalar como versión estable.**

# FBM Card

Tarjeta para Home Assistant con calendarios, resultados y clasificaciones de la Federación de Baloncesto de Madrid (FBM).

**Estado: desarrollo (rama dev). Búsqueda y horarios comprobados mediante diagnóstico; integración completa pendiente de validar.**

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

**Estado actual:** hay un prototipo experimental de búsqueda por equipo, categoría y temporada, pero el flujo completo aún no se ha probado en Home Assistant. Pintobasket es solo un caso de prueba y no es un equipo obligatorio o predeterminado.

## Selector de varios equipos (implementado parcialmente en DEV)

En el modo basado en entidades, la tarjeta permite configurar una lista de equipos y alternar entre ellos. La última selección se guarda **en el navegador/dispositivo**, con una clave que incluye el identificador del usuario de Home Assistant y `id_tarjeta`. No hay sincronización entre dispositivos. El modo experimental incorpora búsqueda FBM, pero aún no comparte estas preferencias ni se ha validado en HA. Sin identidad de usuario no se guarda la preferencia.

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

En el modo basado en entidades se puede marcar o desmarcar como favorito cualquiera de los equipos configurados. Los favoritos aparecen primero en el selector, identificados con ★. Se almacenan en el navegador, separados por identificador de usuario de Home Assistant y por `id_tarjeta`. **No se sincronizan entre móviles u otros navegadores** ni están conectados al buscador experimental. Sin identidad de usuario disponible no se muestra el botón para guardar favoritos.

## Restricción de procedencia de datos

El adaptador de datos debe obtener información **exclusivamente de endpoints oficiales de la FBM**. La tarjeta rechaza entidades cuyo atributo `fuente` no sea exactamente `FBM`. **Esta etiqueta es una comprobación de formato, no una prueba criptográfica de origen**: la garantía real depende del adaptador que consulte únicamente la FBM y de pruebas de integración contra sus endpoints oficiales. Está prohibido sustituirlos por fuentes de clubes o terceros.

## Descubrimiento de sensores FBM (DEV)

En el modo basado en entidades, cuando no hay equipos configurados, la tarjeta enumera hasta diez entidades `sensor.*` de Home Assistant con estructura de partidos/clasificación y `fuente: FBM`. Esta enumeración solo inspecciona sensores existentes y una etiqueta declarada no certifica la procedencia. El buscador experimental es un flujo separado y está pendiente de validación en HA.

## Modo de descubrimiento automático (DEV)

Si ya existen sensores de equipos con el contrato FBM, se puede activar el selector sin enumerarlos manualmente:

```yaml
type: custom:fbm-card
title: Mis equipos FBM
id_tarjeta: mis_equipos
descubrir_entidades: true
```

En este modo la tarjeta muestra los sensores con `fuente: FBM` y estructura válida, permite cambiar entre ellos y marcar favoritos. **No descarga equipos de la FBM** ni verifica criptográficamente el origen de un sensor. No sustituye el conector oficial pendiente.

## Diagnóstico de API oficial (DEV)

`python3 scripts/diagnostico_fbm.py` realiza una petición de búsqueda sin credenciales a `https://appaficionfbm.gesdeportiva.es/v2/busqueda.ashx` e informa si la API devuelve un error o una respuesta interpretable. No requiere paquetes adicionales. Un error por parámetros **no equivale a acceso funcional a resultados**. No se usan fuentes externas ni claves ficticias. El diagnóstico no es un conector de datos ni está integrado en la tarjeta.

## Registro automático de tarjeta (DEV)

La integración intenta registrar `/fbm_static/fbm-card.js` como recurso de tipo `module` en los recursos Lovelace gestionados por almacenamiento. Evita duplicados y no modifica dashboards YAML. **La implementación está pendiente de validación en una instalación real de Home Assistant**; si el modo de recursos no permite el registro, puede requerirse añadir manualmente la URL del recurso. No equivale todavía a una instalación Marketplace verificada.
