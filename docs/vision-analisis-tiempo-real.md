# Ampliación de alcance: directo y análisis mediante MCP

Estado: requisitos de diseño, no funcionalidades implementadas ni acceso API verificado.

## Objetivos
- Selección de varios equipos por usuario; favoritos privados.
- Marcador en directo, estado, periodo, reloj y eventos **solo si la fuente oficial los ofrece**; mostrar marca temporal, latencia y estado de conexión.
- Calendarios, resultados, clasificaciones, históricos y estadísticas de equipos/jugadores, exclusivamente cuando estén disponibles públicamente desde la FBM.
- Consultas conversacionales mediante MCP de Home Assistant: último partido, comparativas, tendencias, próximo rival y jugadores destacados.
- Informes postpartido opcionales con consentimiento del usuario.

## Arquitectura
1. Adaptador FBM: comprobar endpoints oficiales web o de la aplicación en modo invitado, esquema, condiciones de uso y frecuencia admisible. No extraer credenciales ni eludir autenticación.
2. Coordinador HA: consultas centralizadas, caché, reintentos, límites y actualización adaptativa (más frecuente durante partidos solo si está permitido).
3. Persistencia: conservar históricos estructurados fuera de atributos gigantes de entidades; exponer sensores resumidos y acciones/servicios de consulta paginada para MCP.
4. Tarjeta incluida en la integración: selección, favoritos, directo, calendario, clasificación y estadísticas disponibles; indicación explícita de datos ausentes.
5. MCP: comprobar herramientas existentes y, si procede, añadir acceso de solo lectura a consultas estructuradas; no asumir que el MCP actual puede leer históricos.

## Criterios de aceptación
- Prueba de acceso real a la fuente oficial, respuesta verificable y permisos adecuados.
- Ningún dato ficticio ni fuente alternativa.
- Datos en directo identificados como tales solo con confirmación de la FBM y fecha de última actualización.
- Pruebas de actualización, pérdida de conexión, datos parciales, privacidad por usuario y límites de peticiones.
- Validación en HA de integración y registro Lovelace antes de publicar.

## Próximo hito
Investigar técnicamente qué consultas públicas de Afición FBM/Gesdeportiva permiten recuperar equipos, partidos y, eventualmente, seguimiento en directo; documentar evidencias y limitaciones antes de implementar el adaptador.
