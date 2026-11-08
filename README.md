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
