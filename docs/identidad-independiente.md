# Identidad independiente en desarrollo

La integración prepara un gestor de identidad por entrada de configuración, con `Store` privado de Home Assistant y escrituras atómicas. Su creación es explícita: cargar o configurar la integración no genera un identificador ni contacta con FBM. El UID es aleatorio, propio de la instalación y no procede de un Android ID. El almacenamiento contiene el UID y, si se vincula explícitamente, un `id_dispositivo` candidato; no guarda claves de sesión.

El gestor conserva el UID entre cargas, no sustituye una identidad existente, rechaza registros con estructura inválida y no sustituye un candidato diferente. Si detecta un archivo existente que `Store` no pudo cargar, bloquea la creación durante esa instancia. Home Assistant puede preservar un archivo JSON corrupto renombrándolo y devolver una carga vacía: esa situación requiere recuperación, no asumir que se puede registrar un dispositivo nuevo. Esta comprobación no garantiza detectar una corrupción ya renombrada en una ejecución anterior. El almacenamiento privado depende de los permisos y copias de seguridad de Home Assistant; no implica cifrado.

El prototipo no migra los archivos del diagnóstico Windows ni enlaza automáticamente su candidato. La sesión y el funcionamiento de instalación siguen sin probarse en un Home Assistant real. La aceptación de identidades independientes y el ciclo completo de recuperación siguen pendientes de validación.

## Cliente bajo demanda

Cada entrada prepara además un `IndependentClient` con el gestor anterior; construirlo no crea identidad ni realiza peticiones. El cliente ofrece operaciones internas explícitas para crear la identidad, registrar, asociar un candidato, solicitar acceso, buscar equipos y consultar horarios. La sesión se conserva exclusivamente en memoria y se descarta al descargar la entrada. Si falla una reconexión, se olvida la sesión anterior; no registra dispositivos ni renueva la clave de forma automática. La representación de los objetos de perfil y sesión omite UID, token push, clave y dispositivo.

El registro y el puente hacia la tarjeta son experimentales: faltan pruebas con Home Assistant real y validación de un registro independiente completo. Los horarios mantienen las limitaciones de grupos, fechas y rondas documentadas en `protocolo-dispositivo-apk.md`.

## Puente y tarjeta experimental

La integración registra comandos WebSocket `fbm/client/entries`, `fbm/client/status`, `fbm/client/create_identity`, `fbm/client/register`, `fbm/client/connect`, `fbm/team/search`, `fbm/team/phases`, `fbm/team/schedule` y `fbm/team/schedule_round`, limitados por ahora a administradores. Las operaciones de creación, registro, conexión y consulta son separadas. Las respuestas no incluyen UID, clave de sesión ni candidato de dispositivo; las búsquedas y los partidos sí devuelven los identificadores deportivos necesarios para seleccionar y consultar. Los errores enviados al navegador son genéricos. El registro experimental acepta únicamente JSON con error vacío, `key` no vacía e `id_dispositivo` no vacío; ese contrato de registro inicial todavía no se ha comprobado en una respuesta real satisfactoria. Si la petición llega al servidor y luego falla, puede haber quedado registrado aunque no se haya guardado el candidato; no se reintenta automáticamente.

La tarjeta puede habilitar el prototipo mediante la configuración siguiente:

```yaml
type: custom:fbm-card
modo_experimental: true
```

El prototipo permite comprobar el estado, crear una identidad local, registrar expresamente, conectar, buscar equipos por nombre y seleccionar categoría/temporada, consultar la fase y escoger explícitamente una ronda cuando la haya, y solicitar horarios. La ruta de rondas se basa en análisis estático y simulaciones; no se ha validado con un equipo real con rondas. La tarjeta no importa la identidad Windows del diagnóstico: crea otra distinta para esa instalación. No se ha probado el alta nueva, la compatibilidad concreta con versiones de Home Assistant ni la tarjeta en una instalación real. Muestra partidos de grupo porque es lo que devolvió la operación observada, y advierte de que pueden aparecer fechas fuera del rango. La clasificación y resultados en directo no están validados y `00:00` no se interpreta como hora confirmada o pendiente.

Las peticiones del cliente y del diagnóstico usan un abridor que rechaza redirecciones HTTP: una respuesta 3xx no reenvía automáticamente identificadores ni claves a otra URL. El acceso por WebSocket queda limitado a administradores durante esta fase. La tarjeta no envía peticiones FBM al cargarse: cada operación requiere su botón, y el registro y la conexión son acciones distintas. El componente se ha comprobado mediante simulaciones; no hay prueba de instalación ni verificación de compatibilidad con una versión concreta de Home Assistant. La suite Python asíncrona completa no ha terminado en el entorno local.
