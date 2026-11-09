# Grupos seguidos — estado de desarrollo (DEV, 09/11/2026)

## Implementado
- `custom_components/fbm/followed_groups_store.py`: SQLite independiente para seguimiento explícito por clave (temporada, grupo), snapshots de clasificación, fecha UTC y preservación histórica después de dejar de seguir.
- `tests/test_followed_groups_store.py`: 4 pruebas (seguimiento opt-in, conservación al dejar de seguir, aislamiento y persistencia, rechazo de datos anteriores/fuentes no verificadas).
- CI para commit `487686dadf0c0ddb2dbed7773f42685718f58768`: dos workflows terminados en **success**. Esto valida el código/CI, **no** la sincronización real en Home Assistant.
- Las búsquedas de equipo y sus preferencias siguen intactas. No se ha tocado la identidad FBM, `main`, ni la configuración actual de tarjetas.

## No implementado ni validado
- Almacenamiento aún **NO integrado** en `__init__.py`, coordinador, sensores ni WebSocket. No se ha desplegado en HA, ni siquiera en DEV.
- El identificador de temporada necesita verificación real; no migrar datos con claves supuestas.
- Política de intervalos laborables/fin de semana, opciones de integración y actualización manual, resumen de salud por grupo y fuente; todos pendientes.
- Calendario de grupo: consulta fallida; jugadores/estadísticas: campos presentes en APK pero respuestas/cobertura aún no validadas; **no almacenar ni presentar como funcional**.
- Recuperación automática de sesión tras reinicio con identidad guardada: sin prueba extremo a extremo nueva.
- La búsqueda en tiempo real nunca debe crear seguimientos ni sensores; si usa caché, mostrar fecha/antigüedad.

## Capacidades MCP verificadas
El conector Home Assistant ofrece `ha_get_state` para estado y atributos de entidades, `ha_get_history` para historial del recorder y `ha_list_services`/`ha_call_service` para acciones registradas. Consulta real a `ha_list_services(domain="fbm")` devolvió **0 servicios**. No se ha identificado comando MCP que ejecute directamente `fbm/group/... ` por WebSocket ni API detallada SQLite. Una entidad resumen con fecha/estado podrá consultarse cuando exista; para partidos y jugadores detallados se necesita una interfaz adicional cuya exposición al conector se compruebe realmente.

## Próximas tareas en orden
1. Probar recuperación de sesión existente y verificar IDs oficiales de temporada/grupo.
2. Integrar el almacén en un coordinador opt-in (sin trabajos programados antes de selección), opciones de intervalos y errores aislados por fuente.
3. Crear sensores de resumen con `last_success`, `last_attempt`, `stale`, `status` y `source_status`; acción manual; sin datos personales innecesarios en atributos.
4. Solucionar calendario con respuesta oficial observada, antes de activar ingesta. Validar disponibilidad/privacidad de jugadores por categoría.
5. Tarjetas lectoras del almacén y favoritos solo visuales; mantener búsqueda en tiempo real separada. Probar extremo a extremo con HA DEV.

No dar por desplegado ni operativo nada de los puntos pendientes.