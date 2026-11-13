# FBM Card v0.2.2b26 (Beta) — Complete incremental and differential archive

## English

### Goal: all available official data, not just a sample
Every **explicitly followed FBM competition** is synchronized across **all its ranked teams and rostered players**, including refreshed group standings, finished and upcoming fixtures, team rosters, and official per-game player statistics. The existing opt-in boundary is preserved: other competitions are never enrolled automatically.

### Changes
- Keep the existing incremental player cursor and **five-player maximum every 30 minutes**. New games and missing snapshots are downloaded without duplicating unchanged archive records.
- **Weekly periodic full revalidation of the player-stat archive**, including previously downloaded players whose official appearance count has not changed. This detects retroactive score/statistic corrections from FBM without requiring a new match. Revalidation is split across the existing small batches, not downloaded in one burst.
- **Weekly full team-roster recheck** of each followed group even if fixture scores have not changed, so late registrations and roster corrections can be picked up. Normal checks remain differential, using changes in official fixtures.
- Restart-safe persisted cursor and full-recheck mode; retains one retry for a partially failed batch and the daily cycle delay. Players with zero official appearances do not trigger error-like FBM API calls but become eligible when a first appearance is recorded.
- Identical payloads do not create redundant SQLite history; changed data creates a new, retained snapshot.
- Keeps v0.2.2b25's privacy-safe match-level score discrepancy auditing. A mismatch is visible, **not fixed by inventing or estimating points**.
- Includes tests covering forced rechecks of cached players, first-appearance eligibility, restart/retry persistence, and weekly roster checks, plus Python/JS and real Home Assistant Core CI.

### Important distinction
**Data pending to download** vs. **data unavailable from FBM** vs. **data inconsistent with official team scores** are different states. Complete download of everything *available* does not mean the source necessarily publishes every individual match statistic. For example, the Oct 17 Colegio Áquila–Ciempobasket match still has a bilateral discrepancy in the source-derived records; this release does not modify those numbers.

### Install and rollback
Prerelease. Back up Home Assistant before installing; keep v0.2.2b25 available to revert. No SQLite schema migration. After installation, check sensor.competiciones and allow the bounded scheduled cursor to progress; an initial full revalidation across a large group can take more than one day.

## Español

### Objetivo: todos los datos oficiales disponibles
Las competiciones FBM **marcadas expresamente para seguir** se mantienen sincronizadas con **todos sus equipos y jugadores**, incluidas clasificaciones, calendarios, plantillas y estadísticas oficiales por encuentro. No se añaden automáticamente competiciones ajenas a la selección del usuario.

### Novedades
- Se mantiene el cursor incremental con **un máximo de cinco jugadores cada 30 minutos**. Se incorporan nuevas estadísticas sin duplicar instantáneas que no hayan cambiado.
- **Revalidación completa semanal de las estadísticas individuales archivadas**, incluso cuando el número de partidos del jugador sea igual al de la caché, para recoger correcciones retroactivas de FBM. Se reparte en lotes pequeños.
- **Revisión completa semanal de las plantillas de todos los equipos** de cada competición seguida, aunque no haya cambiado ningún marcador. Entre revisiones completas se mantiene la comprobación diferencial basada en cambios del calendario.
- Cursor persistente entre reinicios, modo de revalidación semanal conservado, reintento único ante fallo parcial y pausa diaria entre ciclos. Los jugadores con cero partidos no generan peticiones fallidas; se consultan automáticamente cuando figure su primer encuentro.
- Historial SQLite conservado; únicamente se guardan nuevas versiones cuando cambia realmente el contenido.
- Se conserva la auditoría b25 de discrepancias entre marcador y puntos individuales, sin inventar estadísticas.
- Pruebas de regresión y de Home Assistant Core para revalidación, reinicios, reintentos y refresco de plantillas.

### Limitaciones reales
**Pendiente de descargar**, **no publicado por FBM** y **datos contradictorios** son situaciones distintas. La integración buscará todos los datos que publique FBM, pero no puede completar estadísticas que el origen no proporcione. La discrepancia bilateral del partido Colegio Áquila–Ciempobasket del 17 de octubre permanece identificada; no se alteran los marcadores.

### Instalación
Versión beta. Se recomienda copia de seguridad antes de instalar. Se puede volver a v0.2.2b25. No cambia el esquema SQLite. Las revisiones completas son progresivas y pueden tardar más de un día en grupos grandes.
