# FBM Card v0.2.2b4 — Beta de actualización automática voluntaria

## Novedades respecto a v0.2.2b3
- Nuevo menú **FBM → Configurar → Actualización automática**, con dos opciones **desactivadas por defecto**.
- **Clasificación y calendario:** actualización cada 4 horas, una competición seguida por ejecución, con ventana de 45 días antes y 60 días después. Sin descarga de plantillas.
- **Estadísticas individuales:** como opción adicional, un único lote de hasta 5 jugadores ya archivados cada 2 horas. Se guarda el avance entre reinicios y se espera al menos 24 horas tras completar una vuelta de todos los grupos.
- Nunca se sigue una competición automáticamente, no se consulta una competición retirada y no se mezclan fases. La opción de jugadores exige activar también resultados.
- Las tareas se cancelan al descargar la integración. Los cambios en seguimiento o la actualización manual no reinician innecesariamente FBM.
- Las tarjetas Lovelace mantienen su JavaScript idéntico a la versión estable.

## Instalación
Versión preliminar voluntaria. Recomendamos confirmar una copia de seguridad antes de actualizar, instalar explícitamente `v0.2.2b4` desde Marketplace y reiniciar Home Assistant. La mera instalación **NO activa** las actualizaciones periódicas: las dos casillas estarán desactivadas hasta seleccionarlas manualmente en **Configurar → Actualización automática**. El cambio de estas opciones recargará la integración.

## Recuperación
Para volver atrás, seleccionar `v0.2.2b3` o `v0.2.1` en Marketplace, instalar y reiniciar. El archivo SQLite existente conserva los históricos. Ninguna tarjeta tiene cambios de JavaScript.

## Límites
Las pruebas automáticas comprueban los temporizadores, el guardado de avance y el flujo de configuración usando simulaciones y Home Assistant Core real. **Todavía no se ha observado un ciclo programado completo en Home Assistant productivo**.

## English
Opt-in scheduled FBM refresh: followed competition fixtures/standings every four hours, at most one group per tick; archived player stats five records per two-hour tick, persisted cursor and a 24-hour full-cycle pause. Both settings default off; enable under FBM Configure → Automatic refresh after installing/restarting this prerelease. Existing cards remain unchanged. Roll back by reinstalling v0.2.2b3 or v0.2.1.
