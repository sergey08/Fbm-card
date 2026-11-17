# FBM Card v0.2.8 — Release notes

## English

- Team cards automatically repaint their results and standings when the local archive changes, even when the FBM session has expired.
- Groups with recently played matches and pending scores become eligible for another update after 30 minutes.
- The scheduler skips groups that do not need refreshing and checks at most one group in each five-minute cycle.
- The existing local history, configured teams and Lovelace cards are preserved. No new manual refresh button is required.

**Validation:** v0.2.8b1 was confirmed functional in the user's Home Assistant. Automated validation and the GitHub publication workflow completed successfully. Installation of v0.2.8 stable in Home Assistant has not yet been confirmed.

## Español

- Las tarjetas de equipo actualizan automáticamente los marcadores y la clasificación cuando cambia el archivo local, incluso con la sesión de FBM caducada.
- Los grupos con partidos recientes pendientes de marcador pueden volver a consultarse transcurridos 30 minutos.
- El programador omite grupos que no necesitan actualización y consulta como máximo un grupo en cada ciclo de cinco minutos.
- Se conservan el histórico local, los equipos configurados y las tarjetas Lovelace. No se necesita un botón manual de actualización.

**Validación:** el usuario confirmó que v0.2.8b1 funciona en su Home Assistant. La validación automática y el flujo de publicación de GitHub terminaron correctamente. La instalación de v0.2.8 estable en Home Assistant todavía no se ha confirmado.
