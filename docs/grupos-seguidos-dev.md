# Competiciones seguidas y archivo local

Referencia técnica de los grupos seguidos en FBM Card. Describe el comportamiento integrado hasta v0.2.14 y la descarga inicial continua validada en la beta v0.2.15b1.

El seguimiento explícito de un equipo y su competición da acceso a la sincronización de todos los equipos del grupo oficial seleccionado. El contexto persistente combina temporada, fase y grupo. Las fuentes deportivas son las respuestas del servidor de FBM.

## Identificación y seguimiento

La búsqueda oficial devuelve equipos con una etiqueta visible de temporada, como `26/27`. [competition_manager.py](../custom_components/fbm/competition_manager.py) valida que esa etiqueta represente años consecutivos y la asocia con la fase y el grupo actuales que devuelve `fasesGrupos`.

La respuesta de fases y grupos puede carecer de un identificador independiente de temporada. En ese caso se conserva la etiqueta oficial seleccionada. Los identificadores de temporada y componente de club necesarios para estadísticas de un jugador se obtienen de su ficha y se validan dentro de ese contexto.

Al volver a sincronizar se comprueba que el equipo siga perteneciendo a la competición guardada. Un cambio de fase o grupo se comunica como transición y requiere seleccionar el nuevo contexto. La consulta previa de un equipo permite ver el grupo antes de confirmar su seguimiento.

Implementación en [competition_manager.py](../custom_components/fbm/competition_manager.py), [followed_groups_store.py](../custom_components/fbm/followed_groups_store.py) y [config_flow.py](../custom_components/fbm/config_flow.py).

## Consultas al servidor

El contrato de transporte, los formularios y las respuestas se describen en [protocolo-dispositivo-apk.md](protocolo-dispositivo-apk.md).

La descarga del grupo utiliza este recorrido:

1. Resolver la fase y el grupo oficial del equipo elegido.
2. Leer la clasificación para enumerar los equipos participantes.
3. Solicitar el calendario del grupo para la temporada seleccionada.
4. Descargar las plantillas de todos los equipos del grupo.
5. Recorrer los jugadores y descargar sus estadísticas cuando estén publicadas y su contexto esté validado.
6. Guardar el progreso y publicar la cobertura del archivo.

Las respuestas normalizadas conservan los identificadores, fechas, horas, sedes, marcadores, escudos y estadísticas que admite la integración. Un campo ausente permanece desconocido.

## Archivo SQLite

[competition_archive.py](../custom_components/fbm/competition_archive.py) guarda instantáneas por competición, fuente y sujeto. Entre las fuentes están `standings`, `fixtures`, `roster` y `player_stats`.

Las escrituras son transaccionales y comprueban que el grupo continúe seguido. Una respuesta idéntica se deduplica. Una descarga fallida conserva la última instantánea válida. Las plantillas se guardan individualmente y las estadísticas se consolidan durante cada lote, de modo que un fallo posterior permita reanudar el trabajo ya comenzado.

Los fallos del último intento de estadísticas se conservan como estado técnico acotado. Una respuesta válida limpia el fallo anterior. Los detalles crudos de ficha utilizados para resolver el contexto de estadísticas son transitorios.

Implementación de descarga en [competition_sync.py](../custom_components/fbm/competition_sync.py) y [competition_player_stats.py](../custom_components/fbm/competition_player_stats.py).

## Descarga inicial continua en v0.2.15b1

La descarga inicial usa la función existente de lotes de hasta cinco jugadores. Mantiene la pausa de medio segundo entre jugadores consultados y añade dos segundos entre lotes consecutivos. Puede arrancar al iniciar la integración, confirmar nuevas opciones de seguimiento o completar una descarga de plantillas.

El cursor inicial se guarda por separado del mantenimiento programado. Incluye el grupo, equipo, desplazamiento del lote y estado de reintento. El siguiente lote continúa desde el progreso persistido tras reiniciar Home Assistant.

Un bloqueo compartido serializa las peticiones de jugadores con el mantenimiento. Los fallos aumentan la espera desde diez segundos hasta cinco minutos. Cada lote fallido tiene un reintento inmediato con esa espera antes de avanzar a otros jugadores. La descarga se cancela al descargar la integración y vuelve a comprobar los grupos seguidos antes de continuar.

Completar el primer recorrido significa haber procesado sus plantillas. El porcentaje de cobertura se calcula a partir de las instantáneas deportivas y puede seguir mostrando pendientes si hay errores o datos incompletos en origen. Esos pendientes quedan disponibles para las revisiones programadas posteriores.

## Mantenimiento incremental

El programador consulta como máximo un grupo por turno de cinco minutos y aplica una política de frecuencia según la actividad del calendario. Los calendarios se solicitan para el año deportivo completo. Los grupos con una descarga parcial se vuelven a intentar tras la espera correspondiente.

Después de la descarga inicial, los turnos de estadísticas mantienen su intervalo de diez minutos y sus lotes de cinco jugadores. El recorrido y los reintentos se conservan entre reinicios. Un ciclo completo tiene una espera de 24 horas. Si quedan instantáneas incompletas, la siguiente pasada puede comenzar a las seis horas.

Los registros completos se omiten cuando el número de encuentros únicos cubre las participaciones oficiales y todos sus puntos están presentes. Las plantillas y estadísticas tienen revisiones completas periódicas de siete días para recoger cambios y correcciones tardías.

Los jugadores con cero participaciones conocidas se contabilizan por separado y vuelven a ser elegibles cuando la plantilla registra su primer encuentro.

Implementación en [competition_auto_sync.py](../custom_components/fbm/competition_auto_sync.py) y [competition_refresh_policy.py](../custom_components/fbm/competition_refresh_policy.py).

## Cobertura publicada

El sensor `sensor.competiciones` reúne resúmenes de los grupos seguidos, clasificación, resultados, próximos encuentros y cobertura. La tarjeta de competición comparte estos datos entre las pestañas Clasificación y Próximos partidos.

| Medida | Interpretación |
| --- | --- |
| Equipos y plantillas | Equipos enumerados y plantillas presentes en SQLite |
| Jugadores evaluables | Jugadores con participaciones conocidas que permiten comprobar estadísticas |
| Completos y pendientes | Instantáneas que cumplen o incumplen el criterio de encuentros únicos y puntos disponibles |
| Cero participaciones | Registros de plantilla sin partidos conocidos |
| Clasificación y calendario | Presencia de instantáneas, partidos y jornadas archivados |
| Último intento fallido | Jugadores cuyo último intento de descarga terminó en error |
| Comparación de partidos jugados | Marcadores finales archivados frente a los partidos jugados que indica la clasificación |
| Última actualización | Fecha observada de las instantáneas o del turno correspondiente |

El porcentaje de jugadores mide el criterio anterior. La coincidencia con la clasificación ayuda a detectar encuentros finalizados ausentes. La exhaustividad del calendario requiere cotejar los identificadores publicados por la API para el mismo periodo, temporada y grupo.

## Acceso desde Home Assistant y MCP

El módulo [websocket.py](../custom_components/fbm/websocket.py) expone consultas de las tarjetas y operaciones de administración. Cada comando mantiene sus validaciones de identidad, pertenencia y permisos.

Las consultas administrativas del archivo incluyen `fbm/competition/list`, `fbm/competition/latest`, `fbm/competition/team_roster`, `fbm/competition/team_player_stats`, `fbm/competition/analysis` y `fbm/competition/match_preview`. Permiten recuperar instantáneas y preparar análisis con los datos locales.

Un conector MCP que solo expone estados puede leer los agregados de `sensor.competiciones`. El acceso al archivo detallado o la comparación con una consulta directa de FBM necesita una conexión autenticada que admita los comandos WebSocket correspondientes.

## Verificaciones y límites conocidos

El 17/11/2026 se cotejaron por identificador los calendarios archivados de seis grupos con la API de FBM. En Tercera FEB B-A, las consultas desde Qualis y Las Rozas y la división del periodo por semestres devolvieron los mismos 65 partidos. Este recuento describe lo que ofrecía esa API en esas consultas.

En la prueba de alta de RICOPIA FUNBAL ALCALA CBJA, el calendario archivado coincidió con los 132 partidos que devolvía la API del grupo. Tras instalar v0.2.15b1 y reiniciar, el sensor avanzó de 113 a 116 jugadores evaluables completos, con cero pendientes y cero errores registrados. El grupo contenía doce plantillas y ocho registros sin participaciones.

Estas comprobaciones validan esos casos y el avance observado de la descarga inicial. Un porcentaje agregado de 100 % acredita el criterio de archivo definido arriba. Un cotejo exhaustivo de cada estadística individual exige comparar también sus valores con las respuestas correspondientes del servidor.

Las discrepancias entre un marcador de equipo y la suma de anotaciones individuales se conservan y se señalan en el análisis. La presencia de datos oficiales contradictorios requiere investigar su origen. Los análisis respetan los marcadores y cifras publicados.

Las pruebas automáticas cubren formatos de respuesta, selección de grupo y temporada, transacciones, deduplicación, persistencia, reintentos, cobertura y peticiones tardías del frontend. La validación funcional de versiones se registra además en Obsidian. Las revisiones históricas de este documento permanecen disponibles en Git.
