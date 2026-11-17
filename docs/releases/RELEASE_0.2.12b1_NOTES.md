# FBM Card v0.2.12b1 — normal user access (beta)

## English

- Fixed WebSocket authorization so authenticated Home Assistant users without administrator privileges can read FBM teams, fixtures, standings, rosters, player details and relevant archived competition data.
- Kept administrator-only authorization for identity registration/recovery, manual synchronization, diagnostics, batch updates and archived match-preview reports.
- Added regression coverage for normal user access and protected operations.
- No user role changes, no FBM credential disclosure, and no direct modifications to Home Assistant dashboards.
- **Beta awaiting functional validation in a real non-admin Home Assistant session.** If Susana still sees connection errors, capture the exact failed WebSocket command and error code.

## Español

- Corregidos los permisos WebSocket para que usuarios autenticados sin rol de administrador puedan consultar equipos, calendarios, clasificaciones, plantillas, detalles de jugadores y datos archivados pertinentes.
- Permanecen restringidos a administradores el registro y recuperación de identidad, sincronizaciones manuales, diagnósticos, actualizaciones masivas e informes previos archivados.
- Añadidas pruebas de regresión de consultas para usuarios normales y de operaciones protegidas.
- No se modifica ningún rol, no se revelan credenciales FBM ni se alteran los paneles de Home Assistant.
- **Beta pendiente de validación funcional con una cuenta no administradora en Home Assistant.** Si Susana sigue viendo errores, registrar el comando WebSocket exacto y su código de error.
