# FBM Card v0.2.8b1

## Español

- La tarjeta de equipo actualiza el marcador en pantalla cuando cambia el archivo local, incluso con la sesión de FBM caducada.
- Los grupos con partidos recientes sin marcador pueden volver a consultarse tras 30 minutos. Se comprueba un grupo como máximo cada cinco minutos y se saltan los que aún no necesitan consulta.
- Para validar, abre Partidos en una tarjeta de equipo seguido y comprueba que el marcador aparece sin recargar cuando el archivo recibe el resultado.

## English

- Team cards repaint when the local archive changes, including when the FBM session has expired.
- Groups with recent pending scores become eligible after 30 minutes. The scheduler skips groups that are not due and refreshes at most one group per five-minute tick.
- To verify, leave the Matches tab open for a followed team and check that new scores appear when they reach the archive.
