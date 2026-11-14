# FBM Card 0.2.2 — Versión estable

Primera versión estable de la serie 0.2.2, basada en la beta 0.2.2b28 validada en una instalación real de Home Assistant.

## Novedades
- Seguimiento de múltiples grupos y competiciones, calendarios, resultados, clasificaciones y plantillas.
- Sincronización incremental/diferencial de estadísticas de jugadores, con conservación del histórico y omisión de registros completos.
- Diagnóstico de cobertura por competición y global en el atributo `coverage` de `sensor.competiciones`.
- Tarjetas de búsqueda, equipos y competiciones, con editor visual, escudos y fotografías oficiales cuando estén disponibles.
- README en español y nuevo logotipo original de FBM Card.

## Validación
- Probada en Home Assistant con cinco competiciones seguidas, 30 equipos, 30 plantillas y 321/321 jugadores evaluables con estadísticas completas (100 % al 14/11/2026).
- La actualización automática tras la próxima jornada **sigue pendiente de comprobarse**; la cobertura real depende de la publicación de datos por FBM.
- La publicación estable se condiciona a las pruebas de regresión y una prueba de integración contra Home Assistant Core en GitHub Actions.

## Actualización
Instalar desde Marketplace/HACS, reiniciar si lo solicita y recargar el navegador si persiste una tarjeta en caché. **No eliminar ni volver a registrar la integración**: se conserva la identidad invitada y el archivo existente.

Proyecto comunitario no oficial, sin afiliación con la Federación de Baloncesto de Madrid.
