# FBM Card 0.2.2b2 — Beta de interfaz

## Cambios respecto de 0.2.2b1
- Los menús para **seguir, gestionar, actualizar y dejar de seguir competiciones** muestran nombre de equipo, temporada, fase y grupo; desaparecen los identificadores largos internos de FBM.
- Se migran las bases de datos SQLite existentes sin perder los grupos seguidos ni sus históricos.
- Los grupos seguidos desde b1 recuperan sus nombres públicos al realizar la siguiente actualización manual correcta, sin descargar plantillas.
- Las tarjetas existentes no cambian: su fichero JavaScript es idéntico al de la versión estable 0.2.1.

## Instalación y recuperación
La beta es voluntaria. Instalar esta versión mediante Marketplace seleccionando explícitamente `v0.2.2b2` y reiniciar Home Assistant. Antes de instalar, comprobar que hay copia de seguridad completa disponible. Para volver a la estable, instalar `v0.2.1` y reiniciar. Los datos históricos SQLite nuevos no son necesarios para la estable.

## English
Beta UI cleanup: readable official team, season, phase and group names in all competition options flow dialogs, with safe SQLite migration and backfill on the next successful manual refresh. Existing Lovelace card JavaScript remains identical to stable 0.2.1. Explicit prerelease install and restart required; rollback by reinstalling v0.2.1.
