# Protocolo de acceso y consultas de Afición FBM

Esta referencia describe con redacción propia el contrato que utiliza FBM Card. La investigación inicial tomó como referencia Afición FBM 5.0.42 y se contrastó posteriormente con respuestas del servidor. Los detalles de implementación vigentes están en los módulos enlazados. La disponibilidad de cada dato depende de lo que publique FBM.

## Transporte

El servidor utilizado es `https://appaficionfbm.gesdeportiva.es`. Las consultas emplean HTTPS, método POST y formularios `application/x-www-form-urlencoded`. Las respuestas se interpretan como objetos JSON.

| Ruta | Operaciones utilizadas |
| --- | --- |
| `/dispositivo.ashx` | Registro y acceso de dispositivo invitado |
| `/v2/busqueda.ashx` | Búsqueda de equipos |
| `/v2/equipo.ashx` | Fases, grupos, calendario, clasificación y plantilla |
| `/v2/jugador.ashx` | Ficha y estadísticas de jugador |

Los identificadores deportivos se conservan como cadenas opacas. Cada transporte valida las acciones y su conjunto de campos. Las peticiones tienen tiempo de espera y tamaño de respuesta acotados. El calendario admite hasta 2 MiB. Las redirecciones HTTP se rechazan para evitar reenviar la sesión a otro destino.

## Registro y acceso de dispositivo

El formulario de registro contiene `accion=registrar`, `uid`, `plataforma`, `tipo_dispositivo` y `version`.

El acceso de un dispositivo existente contiene `accion=acceso`, esos mismos datos de perfil y los campos `id_dispositivo` y `token_push`. El token de notificaciones puede estar vacío. El perfil compatible utiliza `tipo_dispositivo=mobile`, la versión de aplicación `5.0.42` y una plataforma con el formato `Android <versión>`.

La respuesta de identidad se valida mediante `error`, `key` e `id_dispositivo`. El registro normal acepta un error vacío y exige clave e identificador no vacíos. La recuperación explícita contempla el estado observado `uuid ya registrado`. Durante el acceso se permite conservar el identificador ya conocido cuando el campo recibido está vacío, pero se rechaza un identificador diferente.

La identidad independiente de FBM Card se crea y persiste mediante las acciones de configuración correspondientes. Una identidad existente se reutiliza al restaurar la integración. El registro de una identidad y su acceso son operaciones distintas.

El cliente mantiene una ventana local de uso de clave de 84.400.000 milisegundos desde la respuesta de identidad. Este plazo es una regla local de compatibilidad. Su vencimiento exige renovar el acceso antes de consultar datos deportivos y no demuestra por sí mismo que el servidor haya revocado la clave.

Implementación en [device_protocol.py](../custom_components/fbm/device_protocol.py), [guest_identity.py](../custom_components/fbm/guest_identity.py), [guest_session.py](../custom_components/fbm/guest_session.py) e [independent_client.py](../custom_components/fbm/independent_client.py).

## Búsqueda de equipos

La operación utilizada por el buscador es `buscarEquipo`. El formulario contiene `accion`, `id_dispositivo`, `key`, `texto` y `skip`. El desplazamiento de paginación se transmite como una cadena que representa un entero no negativo.

La respuesta se normaliza a equipos con su identificador y los nombres oficiales disponibles de club, categoría y temporada. La selección de un resultado aporta el contexto de temporada que usa el seguimiento de competiciones. La búsqueda y la selección de un equipo en una tarjeta tienen un flujo distinto del alta explícita de una competición seguida.

Los constructores también reconocen acciones de búsqueda de club y categoría. Su existencia en el contrato no acredita que todas sus variantes estén conectadas a la interfaz ni que compartan el esquema de resultados de equipos.

Implementación en [team_search.py](../custom_components/fbm/team_search.py) y [aficion_adapter.py](../custom_components/fbm/aficion_adapter.py).

## Fases y grupos de un equipo

La petición `fasesGrupos` incluye `id_dispositivo`, `key` e `id_equipo`. La respuesta válida identifica `faseActual`, `grupoActual` y una lista `listaFasesGrupo`. Las fases contienen identificador, nombre, tipo, grupos y rondas.

La integración comprueba que los identificadores actuales correspondan a una única fase y un único grupo de las listas recibidas. La identidad del grupo se obtiene por identificadores y relaciones verificadas. La temporada visible de la búsqueda se valida por separado.

Implementación en [team_phases.py](../custom_components/fbm/team_phases.py) y [competition_manager.py](../custom_components/fbm/competition_manager.py).

## Calendario

El formulario `horariosJornadas` contiene `id_dispositivo`, `key`, `id_equipo`, `id_fase`, `id_grupo`, `id_ronda`, `fecha_inicial` y `fecha_final`.

Para solicitar el grupo se envía su identificador y se deja vacía la ronda. Para una ronda elegida se envía su identificador y se deja vacío el grupo. La presencia de rondas disponibles en la respuesta de fases no selecciona automáticamente ninguna.

Las fechas se expresan como `AAAA-MM-DD 00:00` al inicio y `AAAA-MM-DD 23:59` al final. El constructor admite un intervalo de hasta 366 días entre ambas fechas. La sincronización de competición consulta julio a junio de la temporada seleccionada.

La respuesta de equipo contiene `partidos`, `jornadaActual` y `error`. Entre los campos de partido admitidos figuran `idPartido`, `nombreEquipoLocal`, `nombreEquipoVisitante`, `numeroJornada`, `fecha`, `hora`, `estado`, `resultados`, `campoJuego`, `direccionCampo` y `fechaHoraUTC`. Los resultados contienen las puntuaciones local y visitante y, cuando existen, los parciales.

El normalizador conserva marcadores y estados reconocidos. Acepta las variantes de nombres camelCase y PascalCase soportadas, con una selección coherente por registro. La variante de calendario por categoría tiene su propio normalizador y puede carecer de jornada actual de equipo.

Implementación en [team_protocol.py](../custom_components/fbm/team_protocol.py) y [team_schedule.py](../custom_components/fbm/team_schedule.py).

## Clasificación

El formulario `clasificacion` incluye `id_dispositivo`, `key`, `id_grupo` y `tipo_fase`. El tipo de fase procede de la fase actual verificada.

La respuesta contiene `clasificacion` y `error`. Cada fila identifica equipo y nombre, posición, partidos jugados, ganados, perdidos y puntos. El escudo es opcional. La integración conserva el orden y las cifras que devuelve FBM.

Implementación en [team_standings.py](../custom_components/fbm/team_standings.py).

## Plantillas, fichas y estadísticas

| Operación | Ruta | Campos deportivos adicionales a la sesión |
| --- | --- | --- |
| `jugadores` | `/v2/equipo.ashx` | `id_equipo` |
| `detalleJugador` | `/v2/jugador.ashx` | `id_jugador` |
| `datosGlobalesJugadorEquipo` | `/v2/jugador.ashx` | `id_jugador`, `id_equipo`, `id_componente_club`, `id_temporada` |
| `datosMediasJugadorPartidos` | `/v2/jugador.ashx` | Los mismos cuatro identificadores deportivos |

La sesión de estas operaciones contiene `id_dispositivo` y `key`, además del campo `accion`. Las plantillas se normalizan a una lista de jugadores con identificador y datos deportivos publicados, incluidas las participaciones cuando constan.

Antes de consultar estadísticas, la ficha debe confirmar la relación exacta entre jugador y equipo y proporcionar el contexto de componente de club y temporada. Esos identificadores proceden de la respuesta oficial. El contexto de estadísticas individuales se valida de forma independiente de la identidad de temporada guardada para seguir el grupo.

La respuesta global se normaliza a un objeto `estadisticas` y un indicador de disponibilidad de datos ampliados. La respuesta por partido se normaliza a una lista `partidos` y su total. La API interna reúne ambos resultados en `globales` y `partidos`. SQLite conserva únicamente los campos deportivos admitidos por su esquema.

Los jugadores con cero participaciones conocidas se contabilizan por separado. Las estadísticas inexistentes, las respuestas incompletas y los errores de descarga tienen significados diferentes. Los valores ausentes se conservan como desconocidos y la cobertura refleja lo que está archivado.

Implementación en [player_protocol.py](../custom_components/fbm/player_protocol.py), [player_context.py](../custom_components/fbm/player_context.py), [player_statistics_bridge.py](../custom_components/fbm/player_statistics_bridge.py) y [competition_archive.py](../custom_components/fbm/competition_archive.py).

## Diagnóstico y comprobación

El cotejo de datos deportivos se realiza contra la API del servidor utilizada por la integración, comparando la misma temporada y grupo con el archivo local. La cantidad de jornadas o el formato esperado de una liga son comprobaciones auxiliares. La disponibilidad efectiva se determina a partir de las respuestas de FBM.

Los diagnósticos publican categorías de error, formas de respuesta y contadores acotados. Las claves de sesión y los identificadores técnicos del dispositivo permanecen en el almacenamiento privado de la integración.

Esta referencia consolida el análisis inicial y las verificaciones posteriores. El historial de Git conserva las revisiones anteriores. El estado de sincronización y las pruebas de cobertura se describen en [grupos-seguidos-dev.md](grupos-seguidos-dev.md).
