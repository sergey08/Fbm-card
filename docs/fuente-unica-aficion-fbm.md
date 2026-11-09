# Fuente única: aplicación Afición FBM

Decisión del usuario, 08/11/2026: **todos los datos deportivos procederán exclusivamente de la misma fuente oficial que utiliza la APK Afición FBM**, sin usar la web FBM, FBM TV, clubes ni agregadores como fuentes alternativas.

## Estrategia técnica
1. Identificar el mecanismo de acceso **sin inicio de sesión** que ofrece la APK oficial: sesión invitada, registro público de dispositivo o parámetros documentados. Que la app funcione como invitado **no demuestra** que la API acepte peticiones arbitrarias de terceros.
2. Documentar solicitudes y respuestas **no sensibles** de un flujo invitado autorizado: método, ruta, nombres de parámetros, códigos HTTP y estructura de respuesta. No subir tokens, cookies, claves, identificadores personales ni material extraído de una sesión ajena.
3. Comprobar si el acceso y la reutilización por clientes externos están permitidos por las condiciones del proveedor. No sortear autenticación, controles de acceso ni protecciones técnicas.
4. Validar secuencia real: competiciones → categorías/grupos → equipos → jornadas → partidos → clasificación → estadísticas disponibles. Identificar el alcance de datos en directo sin suponerlo.
5. Implementar un solo adaptador `AficionFBMAdapter` para el gestor de consultas existente, con límites de peticiones y errores explícitos.
6. Consultar jornadas anteriores bajo demanda con caché temporal, **sin almacenar históricos propios**.

## Estado verificable
- Endpoint candidato identificado: `https://appaficionfbm.gesdeportiva.es/v2/busqueda.ashx`.
- Una solicitud sin parámetros suficientes devolvió `Faltan parámetros`. Esto **no confirma** que exista acceso de terceros en modo invitado.
- El diagnóstico actual no proporciona todavía un flujo invitado completo.
- Ningún dato deportivo real ha sido integrado ni probado en Home Assistant.

## Criterio de avance
Conseguir una consulta reproducible y permitida que devuelva competiciones, equipos o jornadas desde la fuente de la APK. Si requiere autorización del proveedor, obtenerla antes de automatizar la extracción.
