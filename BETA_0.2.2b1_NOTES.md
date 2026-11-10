# FBM Card 0.2.2b1 — versión preliminar

**Beta voluntaria. No es una actualización estable.**

## Cambios
- Gestor nativo desde **Configurar**: buscar equipo, elegir competición, seguir y dejar de seguir con confirmación
- Actualizar manualmente clasificación y calendario del grupo completo; descarga de plantillas desactivada inicialmente
- Archivo local SQLite con históricos, sin duplicados y sin descargar fichas de jugadores para identificar la temporada
- Sensor de Home Assistant con competiciones seguidas, clasificación de equipos y últimos cinco resultados
- Consultas WebSocket para administradores y análisis deportivo basado en los datos realmente publicados por FBM

## Compatibilidad y precauciones
- El archivo JavaScript de las tarjetas existentes es idéntico al de 0.2.1. Se actualiza la integración Python.
- **Antes de instalar:** crear copia de seguridad de Home Assistant
- Requiere reiniciar Home Assistant después de instalar la beta
- El gestor de competiciones todavía debe validarse con una sesión FBM real; la beta es para esa prueba
- Mantiene datos de configuración de la integración existente. Evitar activar descargas de plantillas hasta verificar clasificación y calendario

## Vuelta a estable
Desde Marketplace, elegir **v0.2.1** en las versiones del repositorio, instalarla y reiniciar Home Assistant. Los nuevos datos del archivo `fbm_competitions_*.sqlite` no son necesarios para la versión estable.

---

## English
**Opt-in prerelease** with a native competition manager, on-demand group fixtures, a read-only competition summary sensor and SQLite snapshots. Existing Lovelace card JavaScript is unchanged. Back up before installing and restart Home Assistant after changing versions. Reinstall `v0.2.1` to return to stable. Real FBM sessions and MCP need beta validation before stable release.
