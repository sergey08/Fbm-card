# Protocolo de dispositivo observado en Afición FBM 5.0.42

Fecha: 08/11/2026. Fuente exclusiva: APK aportado por el usuario, `classes2.dex` de `base.apk`. Análisis estático sin solicitudes de red ni uso de credenciales.

## Evidencia directa en bytecode

Se han seguido los métodos de inicialización `LZ3/B;->invokeSuspend` y `LZ3/D;->invokeSuspend`, a través de `Ld4/c;->b` y `Ld4/c;->a`, hasta `Lc4/c;->b` y `Lc4/c;->a`, respectivamente.

| Método DEX | Operación literal | Campos de formulario observados | DTO de respuesta |
|---|---|---|---|
| `Lc4/c;->b` (code offset 2701660) | `registrar` | `accion`, `uid`, `plataforma`, `tipo_dispositivo`, `version` | `GuardarDispositivoResponseDto` |
| `Lc4/c;->a` (code offset 2700956) | `acceso` | `accion`, `uid`, `token_push`, `id_dispositivo`, `plataforma`, `tipo_dispositivo`, `version` | `IniciarSesionDispositivoResponseDto` |

Ambos métodos construyen `HttpRequestBuilder`, seleccionan `HttpMethod.Post`, establecen `Content-Type: application/x-www-form-urlencoded`, construyen `FormDataContent` y procesan la respuesta con Ktor. Los offsets son desplazamientos del DEX extraído, no direcciones web.

## Interpretación limitada
- La aplicación incluye un flujo de registro y posterior acceso de dispositivo. Esto es **evidencia de un protocolo implementado**, no de que cualquier cliente externo pueda usarlo sin autorización.
- **No se ha verificado todavía la URL efectiva** de estas dos llamadas ni el origen, formato o validez de `uid` e `id_dispositivo`.
- La existencia de `token_push` no demuestra que sea opcional ni permite inventar un valor.
- No generar identificadores, tokens o claves, ni reutilizar secretos de una instalación ajena.
- No se han realizado peticiones reales a la API.

## Próximo análisis
1. Resolver el valor de URL suministrado a `HttpRequestKt.url` para ambos métodos y contrastarlo con `dispositivo.ashx` / `autenticar.ashx`.
2. Seguir el origen de `uid`, `id_dispositivo` y el flujo de almacenamiento local, sin extraer valores privados.
3. Inspeccionar los campos de ambos DTO y comprobar si la respuesta contiene identificadores reutilizados en las consultas deportivas.
4. Validar las condiciones de acceso y efectuar una prueba autorizada desde un entorno con conectividad.

Rama `dev`; `main` y Home Assistant sin modificar.

## Comprobación adicional del APK original

Se ha reabierto directamente `/mnt/data/fbm_analysis/base.apk` y leído `classes2.dex` como tabla de cadenas DEX. Se confirman las siguientes referencias (índices de cadena, no offsets de instrucciones):

- `39654`: `https://appaficionfbm.gesdeportiva.es/dispositivo.ashx`.
- `39651`: `https://appaficionfbm.gesdeportiva.es/autenticar.ashx`.
- `18566`: clase `GuardarDispositivoResponseDto`.
- `18567`: clase `IniciarSesionDispositivoResponseDto`.
- `12270` y `12852`: cadenas `toString` de esos DTO, ambas comienzan por `duracionIntersticia=`.

**Importante:** la presencia de `dispositivo.ashx` junto a las operaciones `registrar` y `acceso` no basta para demostrar que ambas se envíen a esa URL. Es necesario seguir el argumento de `HttpRequestKt.url` y su origen. No se han enviado peticiones, ni leído tokens, ni reconstruido claves.

## Cadena de inicialización corroborada por trazas de ejecución estática

La inspección del flujo `LZ3/B;->invokeSuspend` muestra, en este orden de código, la versión literal `5.0.42`, la llamada `Ld4/c;->b`, una comparación con `correcto` y, más adelante, referencias a `key`, `dispositivoId` y al texto de error `UID no válido`. En `LZ3/D;->invokeSuspend` aparece la lectura de `idDispositivoDbFBM`, la versión `5.0.42`, la llamada `Ld4/c;->a`, la comparación con `correcto` y las referencias `key` y `dispositivoId`.

**Deducción, aún no contrato probado:** el flujo parece distinguir entre alta de dispositivo y acceso de un dispositivo previamente almacenado; en ambos casos se procesaría una respuesta que puede alimentar `key` y `dispositivoId`. La mera proximidad de instrucciones no demuestra asignación de campos, obligatoriedad de parámetros ni su procedencia.

**Bloqueo concreto:** falta desensamblar con seguimiento de registros el valor pasado a `HttpRequestKt.url` en `Lc4/c;->a/b` y los accesos al DTO. No sustituir esa comprobación por solicitudes inventadas.

## Validación negativa del mapeo directo de URL (08/11/2026)

Se ejecutó de nuevo sobre `classes2.dex` la comprobación que exige que una instrucción `const-string` de URL esté seguida inmediatamente por `sput-object` del mismo registro. Para `dispositivo.ashx` y `autenticar.ashx`, **el resultado fue una lista vacía**. Esto significa exclusivamente que **no se ha demostrado una asignación estática directa con ese patrón**; no que las rutas no se utilicen. El patrón sí había encontrado cinco asignaciones para `v2/busqueda.ashx`, por lo que es una comprobación útil, aunque incompleta.

La búsqueda de referencias dentro de instrucciones reconocidas por el inventario parcial `method_owners.json` tampoco devuelve coincidencias para las dos rutas de dispositivo. Se debe ampliar el rastreo a `const-string/jumbo`, otras clases DEX, construcción dinámica y propagación de registros. **No se atribuye ninguna URL a las operaciones `registrar` o `acceso` sin esa prueba**.

## URL de registro y acceso resuelta por seguimiento de registros (08/11/2026)

**Confirmado en instrucciones DEX alineadas**, no por proximidad de cadenas:

1. `Lc4/c;-><init>` (código desde offset decimal `2702352`) ejecuta `const-string v1, "https://appaficionfbm.gesdeportiva.es/dispositivo.ashx"` en `2702362`, seguido de `iput-object v1, v0, Lc4/c;->b:Ljava/lang/String;` en `2702366`. El campo `a` es el cliente HTTP Ktor.
2. En `Lc4/c;->a` (`acceso`), en `2701116` se lee `iget-object v5, v1, Lc4/c;->b:Ljava/lang/String;`; en `2701148`, `HttpRequestKt.url` recibe `v9` (request builder) y `v5` (URL).
3. En `Lc4/c;->b` (`registrar`), en `2701818` se lee el **mismo campo** `Lc4/c;->b` a `v5`; en `2701850`, `HttpRequestKt.url` recibe igualmente `v9` y `v5`.
4. Ambos métodos fijan `POST` y construyen `application/x-www-form-urlencoded` (documentado anteriormente).

**Conclusión confirmada:** `registrar` y `acceso` de la versión APK 5.0.42 se envían a `https://appaficionfbm.gesdeportiva.es/dispositivo.ashx`. Esto corrige la limitación del apartado anterior: la URL no se asigna a un campo estático mediante `sput-object`, sino al campo **de instancia** mediante `iput-object` en el constructor.

**Pendiente:** origen exacto de `uid`, semántica de `token_push`, campos de respuesta y verificación de acceso autorizado. No se ha realizado tráfico de red ni extraído claves.
