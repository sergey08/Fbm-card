# Historial deportivo y análisis MCP (DEV)

Se ha añadido `custom_components/fbm/history.py`, un almacén **en memoria** de revisiones de partidos con identificadores oficiales estables. Es infraestructura aislada, no una integración funcional con la FBM.

- Capacidad por defecto: 500 partidos y 12 revisiones por partido; configurable a la baja.
- Si solo cambia `fetched_at`, no crea una revisión adicional.
- Ignora actualizaciones anteriores a la última revisión y entrega copias de los datos.
- No realiza consultas HTTP, no inventa marcadores y no se conecta todavía a sensores ni al MCP.
- **No persiste tras reinicios.** La persistencia segura y las consultas históricas paginadas serán una fase posterior.
- Los registros son aceptados desde código interno y **no autentican por sí mismos su procedencia**: el adaptador oficial debe normalizarlos y verificar su origen.
- No registrar datos personales de jugadores hasta conocer la cobertura oficial y sus condiciones de uso.

Pruebas: `tests/test_history.py` (duplicados, revisiones, antigüedad, límites, copia defensiva y validación básica). El flujo CI las ejecutará como parte de `unittest discover`; aún no se ha verificado su ejecución.

## Próximos hitos
1. Obtener acceso autorizado y respuesta verificable de la fuente FBM.
2. Añadir coordinador de actualización con caché y limitación de peticiones.
3. Persistir historiales estructurados con migraciones y retención.
4. Exponer consultas de solo lectura a través de Home Assistant para que el MCP pueda analizarlas.
