# Acceso de usuarios no administradores a FBM Card

## Español

Las tarjetas FBM necesitan consultas WebSocket con la sesión autenticada de Home Assistant, pero **no** necesitan privilegios de administrador para consultar los datos deportivos. Anteriormente, el puente exigía `require_admin` incluso para listar la integración y consultar clasificaciones; un usuario normal veía «Reintentar conexión».

Esta corrección permite a usuarios autenticados consultar la entrada FBM, su estado seguro (sin credenciales), equipos, calendario, fases, clasificación, detalles y estadísticas deportivas, competiciones archivadas seguidas y sus plantillas/estadísticas. Se mantiene la validación de cada identificador y el tratamiento genérico de errores.

Siguen reservados al administrador el alta/registro/recuperación/conexión de identidades, sincronización manual, operaciones de diagnóstico y las consultas de archivo amplias que no son necesarias para mostrar las tarjetas. No se amplían permisos de Home Assistant ni se facilitan tokens de FBM.

### Validación pendiente

1. Ejecutar la CI del PR y revisar las pruebas con usuario `is_admin=False`.
2. Instalar una beta desde GitHub/Marketplace tras aprobar el PR.
3. Abrir `/lovelace/fbm` con una cuenta normal (Susana) y comprobar búsqueda, Gael, Zoe, clasificación y jugadores.
4. Confirmar que el administrador sigue pudiendo hacer sincronizaciones y que el usuario normal no.

Nota: los `id_tarjeta` duplicados y los equipos sin `equipo_fijo` son cuestiones de configuración independientes. No se modifica el panel estable durante esta corrección del backend.

## English

Authenticated Home Assistant users can now read FBM sports data through WebSocket without the admin role. Administrator privileges remain required for identity provisioning, manual sync, diagnostics and broad archive operations. Credentials are never returned. Regression tests cover ordinary-user reads and protected administrative commands.

Functional validation with a non-admin session is required before a stable release.
