# FBM Card v0.2.12 — authenticated non-admin access

## English

- Fixed the WebSocket permission issue affecting standard Home Assistant accounts: signed-in non-admin users can read FBM team search, calendars, standings, rosters, player details and relevant archived competition data.
- Administrator privileges remain mandatory for provisioning and reconnecting the FBM identity, manual synchronization, diagnostics, batch updates and archived match-preview reports.
- Added regression tests for both standard-user reads and protected administrative actions, preserving the existing security boundary.
- Promoted the behavior of beta **v0.2.12b1**, successfully validated on 14 November 2026 in the real Home Assistant session of a non-administrator user (Susana), to stable.
- No dashboard migration, role changes or new credentials are required.
- FBM Card is a community project and is **not officially affiliated with FBM**. Until acceptance in the HACS default catalog, install as a custom integration repository.

## Español

- Corregido el problema de permisos WebSocket que afectaba a las cuentas normales de Home Assistant: los usuarios autenticados no administradores pueden consultar el buscador FBM, calendarios, clasificaciones, plantillas, fichas de jugadores y datos archivados pertinentes.
- Siguen siendo exclusivas de los administradores la provisión y reconexión de la identidad FBM, la sincronización manual, los diagnósticos, las actualizaciones masivas y los informes previos archivados.
- Añadidas pruebas de regresión para consultas de usuarios normales y acciones administrativas protegidas, conservando el modelo de seguridad.
- Promovido a estable el comportamiento de la beta **v0.2.12b1**, validado el 14 de noviembre de 2026 en una sesión real de Home Assistant sin permisos de administrador (Susana).
- No se requiere modificar paneles, permisos de usuario ni credenciales.
- FBM Card es un desarrollo comunitario **no oficial**. Hasta su aceptación en el catálogo oficial de HACS, se instala como repositorio personalizado de tipo integración.
