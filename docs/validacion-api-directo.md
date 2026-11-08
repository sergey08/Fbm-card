# Validación de la fuente FBM y seguimiento en directo

Fecha: 2026-11-08. Estado: **sin acceso funcional confirmado**.

## Evidencias revisadas
- El repositorio dispone de `scripts/diagnostico_fbm.py`, que envía POST a `https://appaficionfbm.gesdeportiva.es/v2/busqueda.ashx` con `accion=buscarEquipo`, `texto=PINTOBASKET`, `skip=0`.
- El script distingue errores HTTP, fallos de conectividad, JSON inesperado y respuestas JSON; una respuesta no demuestra por sí sola que la búsqueda funcione.
- Una consulta externa al endpoint no pudo acceder a él; la web `www.fbm.es` devolvió HTTP 403 desde el entorno de consulta. Estos fallos **no prueban** que la API esté cerrada para la aplicación oficial ni que permita consultas públicas.
- No se ha demostrado acceso a marcadores en directo, eventos, estadísticas de jugadores ni condiciones de reutilización.

## Pruebas siguientes (sin credenciales ni evasión de controles)
1. Ejecutar el diagnóstico desde un entorno autorizado y guardar código HTTP, tipo de respuesta y campos no sensibles; no publicar tokens, cookies ni datos personales.
2. Localizar documentación o endpoints públicos oficiales de FBM/Gesdeportiva y sus condiciones de uso.
3. Confirmar búsqueda real de clubes/equipos y obtener identificadores oficiales estables.
4. Validar calendario, resultados y clasificación con referencias cruzadas dentro de la propia FBM.
5. Durante un partido con seguimiento público, comprobar si existe marcador en directo, periodo, reloj, eventos y sello temporal; medir frecuencia observada sin sobrecargar el servicio.
6. Si existen estadísticas individuales públicas, definir su disponibilidad por categoría y competición, sin asumir cobertura universal.

## Decisiones de diseño
- Separar `scheduled`, `live`, `finished`, `postponed`, `unknown` y estado de conexión; nunca deducir `live` solo por horario.
- Guardar `source_url`, `fetched_at`, `source_updated_at` cuando exista, y calidad/cobertura de cada campo.
- Entidades HA para resumen; consultas estructuradas y paginadas para históricos/MCP. Evitar atributos masivos.
- Frecuencia de sondeo condicionada a la disponibilidad y términos del proveedor; caché, backoff y límite global.
- Mostrar `dato no disponible` en lugar de inventar estadísticas.

## Criterio de desbloqueo
No implementar el adaptador de producción hasta contar con al menos una respuesta oficial real, esquema documentado, condiciones de acceso compatibles y prueba repetible. No modificar `main` ni publicar estable antes de validación en HA.
