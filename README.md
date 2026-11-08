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
