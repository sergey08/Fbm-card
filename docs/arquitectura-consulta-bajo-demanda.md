# Arquitectura simplificada: consulta bajo demanda (decisión 08/11/2026)

## Decisión aprobada
La aplicación oficial Afición FBM permite navegar por todas las jornadas. Por tanto, **no mantener una base de datos histórica propia** en Home Assistant como requisito del proyecto.

### Responsabilidades
- **Fuente oficial FBM:** calendario, jornadas pasadas, resultados, clasificación y estadísticas que realmente exponga.
- **Integración HA:** estado actual resumido en entidades; consulta bajo demanda de una jornada, partido, equipo o jugador, usando exclusivamente la FBM.
- **Tarjeta:** navegación entre jornadas y detalle de partido; favoritos por usuario.
- **MCP:** análisis históricos mediante consultas de solo lectura a la integración. No asumir que el MCP existente soporta esas consultas hasta verificar sus herramientas.
- **Caché:** memoria temporal acotada, con caducidad y control de peticiones. No guardar un histórico permanente.

### API de consulta propuesta (diseño, no implementada)
- `fbm/listar_jornadas`: competición y grupo -> jornadas.
- `fbm/consultar_jornada`: competición, grupo, jornada -> partidos.
- `fbm/consultar_partido`: identificador oficial -> resultado y estadísticas disponibles.
- `fbm/consultar_equipo`: identificador oficial -> calendario y resultados.
- `fbm/consultar_jugador`: identificador oficial -> estadísticas **solo si son públicas y su reutilización está permitida**.

Las operaciones se implementarán como consultas de solo lectura compatibles con Home Assistant, con respuestas paginadas y límites de tamaño, si la API oficial permite dichas operaciones.

### Riesgos y límites
- Ver todas las jornadas en la APK no demuestra que su API pueda ser consultada libremente desde un tercero: validar condiciones y acceso.
- Si la FBM no responde, los históricos no estarán disponibles; la caché solo permitirá información reciente mientras no expire.
- No inventar datos en directo ni estadísticas de jugadores.
- Las comparativas y tendencias dependerán de la cobertura oficial real.

### Simplificación del desarrollo
El prototipo `custom_components/fbm/history.py` y su prueba se conservan temporalmente en `dev` como código experimental **no conectado a la integración**, pero se descartan como parte de la arquitectura objetivo. No crear persistencia ni migraciones de histórico salvo necesidad justificada posteriormente.

### Próximo hito
Validar lectura de jornadas y detalles de partidos en la fuente oficial. Después, implementar consultas bajo demanda y caché TTL antes de añadir sensores y consultas para MCP.

## Avance implementado en DEV
- `custom_components/fbm/query_cache.py`: caché temporal LRU con TTL, máximo 128 entradas y 300 segundos por defecto, configurable para el futuro sondeo en directo.
- `__init__.py`: crea una caché por entrada de configuración y la vacía al descargarla.
- `tests/test_query_cache.py`: pruebas de caducidad, aislamiento, expulsión LRU y validación de parámetros.
- **No hay aún peticiones a la FBM, ni consultas de jornadas, ni acceso desde el MCP.** La caché no almacena históricos de forma permanente.
