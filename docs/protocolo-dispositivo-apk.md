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

## Identificación adicional de DTO y campos (análisis directo del DEX)

La lectura de la tabla de cadenas de `classes2.dex` en el APK original identifica los tipos completos:

- `Lcom/indalweb/appaficion/app/app_data/data/dto/GuardarDispositivoResponseDto;` (índice DEX de cadena 18566).
- `Lcom/indalweb/appaficion/app/app_data/data/dto/IniciarSesionDispositivoResponseDto;` (índice 18567).
- El nombre de campo serializable `duracionIntersticia` (índice 34668), con acceso `getDuracionIntersticia` (índice 36698).
- El literal de almacenamiento local `idDispositivoDbFBM` (índice 39714), el nombre de formulario `token_push` (48249) y `uid` (48516).

**Precaución:** los índices de cadenas no prueban por sí solos que un campo esté presente en una respuesta concreta. Para determinar los nombres JSON de `key`, `dispositivoId` y demás atributos hay que resolver las anotaciones de serialización de cada DTO y las lecturas de sus propiedades; el `toString` de una clase no constituye un contrato JSON. No se han recuperado valores de dispositivo ni tokens.

## Campos reales de las dos clases DTO (lectura directa de field_ids)

Se ha leído `classes2.dex` desde el `base.apk` original, interpretando las tablas `string_ids`, `type_ids` y `field_ids` según el formato DEX, filtrando por los tipos `GuardarDispositivoResponseDto` e `IniciarSesionDispositivoResponseDto`. **No se trata de mera coincidencia de cadenas**.

Ambas clases declaran, entre otros, estos campos de instancia con el mismo tipo:

| Campo | Tipo DEX | Interpretación prudente |
|---|---|---|
| `key` | `Ljava/lang/String;` | Candidato a clave devuelta por el servicio; contenido desconocido |
| `idDispositivo` | `Ljava/lang/String;` | Candidato a identificador devuelto; contenido desconocido |
| `resultado` | `Ljava/lang/String;` | Estado textual, semántica no confirmada |
| `error` | `Ljava/lang/String;` | Error textual, semántica no confirmada |
| `perfil` | `Lcom/indalweb/appaficion/app/app_data/data/dto/PerfilDto;` | Objeto de perfil, contenido desconocido |
| `email` | `Ljava/lang/String;` | Campo opcional/no confirmada su presencia |
| `emailVerificado` | `Z` | Booleano |
| `duracionIntersticia` | `I` | Entero |
| `tiempoReseteoIntersticial` | `J` | Entero largo |

También se identifican campos de configuración `mostrarPublicidad`, `mostrarJugadaJugadaVersionGratis`, `mostrarJugadaJugadaVersionPago`, `noticiasXmlActivo`, `noticiasXmlUrl`, `requiereVersionMinimaAndroid` y `versionActualAndroid`.

**Conclusión:** las dos clases de respuesta **declaran** `key` e `idDispositivo`. Falta demostrar mediante las anotaciones del serializador o una respuesta HTTP autorizada el nombre exacto en JSON, su obligatoriedad y la vinculación con las consultas deportivas. No se han obtenido claves reales ni datos de usuario.

## Origen de argumentos: campos DEX anteriores a las llamadas (08/11/2026)

Se han decodificado los índices de campo de instrucciones `iget-object` / `iput-object` reales inmediatamente anteriores a las invocaciones de las corrutinas de registro y acceso. Los offsets son absolutos en `classes2.dex`:

| Método | Offset | Opcode | Campo DEX tipado |
|---|---:|---|---|
| `LZ3/B;->invokeSuspend` (registro) | 2638692 | `iget-object` | `LN4/v;->b:Ljava/lang/String;` |
| registro | 2638712 | `iget-object` | `LZ3/a;->p:LN4/v;` |
| registro | 2638720 | `iget-object` | `LN4/v;->c:LN4/a0;` |
| registro | 2638724 | `iget-object` | `LN4/a0;->e:Ljava/lang/String;` |
| registro | 2638744 | `iget-object` | `LZ3/a;->p:LN4/v;` |
| registro | 2638752 | `iget-object` | `LN4/v;->a:LN4/i1;` |
| registro | 2638756 | `iget-object` | `LN4/i1;->e:Ljava/lang/String;` |
| registro | 2638770 | `iget-object` | `LZ3/H;->e:Ld4/c;` |
| `LZ3/D;->invokeSuspend` (acceso) | 2640310 | `iget-object` | `LZ3/a;->p:LN4/v;` |
| acceso | 2640342 | `iget-object` | `LZ3/a;->p:LN4/v;` |
| acceso | 2640350 | `iget-object` | `LN4/v;->a:LN4/i1;` |
| acceso | 2640354 | `iget-object` | `LN4/i1;->e:Ljava/lang/String;` |
| acceso | 2640370 | `iget-object` | `LZ3/H;->e:Ld4/c;` |
| acceso | 2640374 | `iget-object` | `LN4/v;->b:Ljava/lang/String;` |

**Hallazgo:** ambos caminos leen `LN4/v;->b` y `LN4/i1;->e`, mientras el registro también lee `LN4/a0;->e`. Esto identifica clases y campos concretos que hay que seguir hasta sus constructores o escrituras. **No asignar aún los nombres `uid`, `token_push` ni `id_dispositivo` a esos campos sin decodificar la propagación de registros y el orden de argumentos del `invoke-range`**. La inspección ha sido estática, sin red ni secretos.

## Rastreo de uso posterior de la identidad invitada (08/11/2026)

Se ha revisado el inventario de accesos a los campos estáticos `Ll7/I;->a:Ljava/lang/String;` (field_id `23338`) y `Ll7/I;->b:Ljava/lang/String;` (field_id `23339`), elaborado al recorrer los `code_item` de `classes2.dex`.

**Evidencia adicional:** en el método `LH5/j;->a` (method_id `2524`) aparecen lecturas `sget-object` de ambos campos (offsets DEX `1708102` y `1708192`), y se repiten en otras ramas de la misma rutina. La presencia de **dos campos estáticos compartidos** en una rutina de consultas es una pista concreta para conectar la inicialización con las peticiones posteriores.

El rastreo de escrituras contiene llamadas a `LZ3/b;->z` con literales `key` y `dispositivoId` (por ejemplo offsets `1784504`–`1784512`, `2209894`–`2209902`), que sugieren lectura de propiedades del resultado. **Todavía no está demostrado** que esas propiedades se asignen a `Ll7/I;->a/b` ni qué campo representa cada una: se necesita seguir registros y la asignación `sput-object` correspondiente.

El barrido automático contabilizó `45403` métodos y `26` errores de decodificación de payload; por tanto el inventario no es exhaustivo y no debe presentarse como prueba de ausencia de otros accesos. Ninguna petición HTTP ni dato privado se ha obtenido en esta comprobación.

**Próximo paso técnico:** desensamblar completamente `LH5/j;->a` y las escrituras sobre `Ll7/I;->a/b`, asociar registros de `key` / `dispositivoId` con los campos de formulario de búsqueda y crear un test de contrato sin valores reales antes de probar el acceso.

## Escrituras directas de identidad tras registro y acceso — 08/11/2026

Nueva comprobación del inventario `guest_field_writes.json` y los contextos de instrucciones de `guest_write_context.json`, generados desde el APK original:

| Flujo | Método | Escritura campo `Ll7/I;->a` | Escritura campo `Ll7/I;->b` |
|---|---|---:|---:|
| Registro | `LZ3/B;->invokeSuspend` | `sput-object` offset 2639244, registro v2 | `sput-object` offset 2639312, registro v1 |
| Acceso | `LZ3/D;->invokeSuspend` | `sput-object` offset 2640510, registro v3 | `sput-object` offset 2640578, registro v2 |

En el contexto de ambas rutas aparecen lecturas de propiedades `key` y `dispositivoId` mediante `Lkotlin/jvm/internal/k;->f` y una invocación `Lv8/o;->C0` inmediatamente antes de la primera escritura. En el inventario anterior, `LH5/j;->a` lee los dos campos estáticos.

**Conclusión limitada:** el APK escribe los dos campos compartidos tras los flujos de registro y acceso, y los consulta posteriormente. Para afirmar que `a=key` y `b=idDispositivo` (o viceversa) hace falta seguir el registro de retorno de cada acceso al DTO hasta cada `sput-object`, incluyendo `move-result-object` y conversiones. No inferir el orden por proximidad de literales. Ninguna petición HTTP realizada.

## Correspondencia verificada de registros a campos compartidos (08/11/2026)

Se decodificaron los operandos reales `22c` (`iget-object`) y `21c` (`sput-object`) en `classes2.dex` extraído del APK aportado. Se usó la tabla `field_ids` para resolver los índices, no coincidencias de texto.

| Flujo | Lectura DTO | Campo leído | Escritura estática | Campo escrito |
|---|---|---|---|---|
| Registro `LZ3/B` | 2639204 `iget-object v2,v1` | `Lf4/a;->w:Ljava/lang/String;` | 2639244 `sput-object v2` | `Ll7/I;->a` |
| Registro `LZ3/B` | 2639218 `iget-object v1,v1` | `Lf4/a;->v:Ljava/lang/String;` | 2639312 `sput-object v1` | `Ll7/I;->b` |
| Acceso `LZ3/D` | 2640470 `iget-object v3,v2` | `Lf4/a;->w:Ljava/lang/String;` | 2640510 `sput-object v3` | `Ll7/I;->a` |
| Acceso `LZ3/D` | 2640484 `iget-object v2,v2` | `Lf4/a;->v:Ljava/lang/String;` | 2640578 `sput-object v2` | `Ll7/I;->b` |

Entre lectura y escritura hay comprobaciones de nulidad `Lkotlin/jvm/internal/k;->f` y validaciones `Lv8/o;->C0`; no se aprecia sobrescritura de los registros correspondientes en los tramos analizados. Los literales `key` y `dispositivoId` se utilizan en ese mismo orden en dichas comprobaciones, de modo que la interpretación más fundada es **`Ll7/I;->a = key`** y **`Ll7/I;->b = dispositivoId`**. La correspondencia `w/v` → `key/dispositivoId` aún debe contrastarse con los metadatos de serialización del DTO, para no confundir nombres internos ofuscados con nombres JSON.

**Confirmado sin red:** los flujos de registro y acceso almacenan los mismos dos campos de respuesta en los mismos dos campos estáticos. **Pendiente:** confirmar nombres JSON, cómo se transmiten en `LH5/j;->a` y validar acceso autorizado.

## Contraste con las tres operaciones de búsqueda (análisis local de código DEX)

Se ha contrastado el resultado de identidad con `verified_post_literals.json` y `post_append_sequence.json`, que inspeccionan instrucciones `const-string` alineadas y las invocaciones a `StringValuesBuilder.append` entre la creación del POST y el contenido del formulario.

| Operación literal en el APK | Método DEX | Offset literal de operación | Parámetros literales observados | Número de llamadas `append` |
|---|---|---:|---|---:|
| `buscarClub` | `Lb5/e;->a` | 2688830 | `accion`, `id_dispositivo`, `key`, `texto`, `skip` | 5 |
| `buscarCategoria` | `Lk5/m;->b` | 4832406 | `accion`, `id_dispositivo`, `key`, `texto`, `skip` | 5 |
| `buscarEquipo` | `Lx5/k;->h` | 5682166 | `accion`, `id_dispositivo`, `key`, `texto`, `skip` | 5 |

Las tres rutinas configuran POST con `application/x-www-form-urlencoded`. La coincidencia de nombres de campos es evidencia de un contrato de formulario compartido; la correspondencia exacta de los **valores** debe comprobarse siguiendo los registros hasta cada `append` (el análisis actual solo asocia el literal anterior más próximo).

**Implicación práctica:** el primer cliente funcional debe probar `buscarEquipo` (además de `buscarClub` y `buscarCategoria`) usando una identidad invitada obtenida legítimamente, sin inventar ni registrar claves en los logs. El diagnóstico anterior sin `id_dispositivo` y `key` no era una prueba completa del contrato observado en la APK.

## Hallazgo: la búsqueda procesa la clave con una operación temporal (08/11/2026)

Inspección directa del archivo `/mnt/data/fbm_analysis/post_register_trace.json`, contrastado con el desensamblado de `Ly8/o;->a`:

- En `Lb5/e;->a` (`buscarClub`), después del literal de formulario `key` (offset DEX `2688864`), se obtiene `java.time.Clock.systemUTC()` (2688882), se invoca `Clock.instant()` (2688890), se construye `Ly8/o` con ese `Instant` (2688908) y se llama a `Ly8/o;->a` (2688914). La operación de `append` de `key` se encuentra en 2688950.
- La secuencia contiene además una comparación y una selección de registros entre la llamada a `Ly8/o;->a` y el `append`. **No se ha demostrado aún qué valor concreto se añade**; la lógica es condicional.
- El código de `Ly8/o;->a` hace referencia a campos de instancia, `java.time.Instant`, una comparación y constantes. Es necesario decodificarlo por completo antes de atribuirle una fórmula o describirlo como firma, caducidad o cifrado.

**Implicación:** no es correcto suponer que basta con insertar sin más el `key` devuelto en el formulario de búsqueda. Hay lógica temporal/condicional en su preparación. No se han calculado ni extraído claves, ni realizado peticiones de red. Para el cliente, mantener separadas la identidad de dispositivo y la preparación del parámetro `key` hasta tener el contrato confirmado.

## Corrección técnica: `Ly8/o;->a` no genera una clave (08/11/2026)

Se ha vuelto a desensamblar **el método completo** `Ly8/o;->a` a partir del `code_item` original (`classes2.dex`, bytes `5744720`–`5744768`). El resultado permite corregir la interpretación provisional de la sección «Hallazgo: la búsqueda procesa la clave con una operación temporal»:

- `5744720`: `iget-object` lee `Ly8/o;->e:Ljava/time/Instant;`.
- `5744724`: `invoke-virtual java.time.Instant.toEpochMilli()`.
- `5744730`: `move-result-wide` del resultado numérico.
- La ruta de excepción comprueba `Instant.isAfter(Instant.EPOCH)` (`5744734`–`5744746`) y retorna `Long.MAX_VALUE` o `Long.MIN_VALUE` según corresponda (`5744750` y `5744762`).

**Conclusión comprobada:** `Ly8/o;->a` es un conversor de `Instant` a milisegundos Unix con tratamiento de desbordamiento. **No es un método de firma, cifrado ni derivación de `key`.** Que se invoque mientras se construye el formulario de búsqueda **no prueba que su resultado sea el valor de `key`**; hay que seguir la selección condicional y los registros hasta `StringValuesBuilder.append`. No implementar una transformación de clave basándose en esa proximidad.

La comprobación estática no realizó solicitudes HTTP ni accedió a credenciales.

## Resuelto: valor de `key` en `buscarClub` condicionado por caducidad (DEX)

La inspección de los opcodes y registros del método `Lb5/e;->a` aclara la secuencia que se había interpretado provisionalmente como posible transformación de clave:

- `2688844`: `sget-object v12, Ll7/I;->b:Ljava/lang/String;` prepara `id_dispositivo`; si es nulo, el flujo utiliza la cadena vacía (2688848–2688858).
- `2688864`: literal `key`.
- `2688914`–`2688920`: conversión de la hora UTC actual a milisegundos (`Ly8/o;->a`, `move-result-wide v14`).
- `2688922`: `sget-wide v16, Ll7/I;->c:J`, un umbral temporal compartido.
- `2688926`: `cmp-long v12, v14, v16`, compara hora actual con umbral.
- `2688930`: `if-gez v12` salta la lectura de clave cuando `ahora >= umbral`.
- `2688934`: en la rama `ahora < umbral`, `sget-object v12, Ll7/I;->a:Ljava/lang/String;`.
- `2688942`–`2688950`: comprobación de nulidad y `StringValuesBuilder.append(..., "key", ...)` con valor seleccionado; la rama sin clave conserva el valor vacío previamente inicializado.

**Conclusión:** en esta operación la clave no se cifra ni se deriva del reloj. Se **usa la clave almacenada solo mientras el umbral temporal no ha vencido**, y se envía un valor vacío si falta o ha caducado. El significado preciso y origen de `Ll7/I;->c` (expiración de sesión u otro plazo) todavía debe seguirse hasta sus escrituras; no etiquetarlo como caducidad de autenticación confirmada. Este análisis es estático y no contiene claves reales.

**Siguiente paso:** localizar todas las escrituras de `Ll7/I;->c` y vincularlas con el procesamiento de respuestas; comprobar que `buscarEquipo` y `buscarCategoria` siguen la misma condición antes de implementar una política de renovación. No se han realizado peticiones HTTP.

## Origen del umbral temporal: escrituras en registro y acceso (08/11/2026)

Una nueva exploración de todos los `code_item` de `classes2.dex`, buscando las instrucciones DEX `sput-wide` (`0x68`) dirigidas a `Ll7/I;->c:J` (field ID 23340), ha localizado las escrituras en los mismos flujos que reciben y guardan la identidad invitada:

| Flujo | Escritura `sput-wide` | Instrucciones anteriores |
|---|---:|---|
| Registro de dispositivo, `LZ3/B;->invokeSuspend` | 2639296 | `Ly8/o;->a` (2639280), `move-result-wide` (2639286), `const-wide/32` (2639288), operación de dos registros (2639294) |
| Acceso de dispositivo, `LZ3/D;->invokeSuspend` | 2640562 | `Ly8/o;->a` (2640546), `move-result-wide` (2640552), `const-wide/32` (2640554), operación de dos registros (2640560) |

Se confirma que el campo temporal compartido se actualiza tanto tras registro como tras acceso, en los mismos métodos que almacenan `key` e `idDispositivo`. **No se confirma todavía el cálculo ni la duración exacta**: hace falta seguir los registros de la operación y descartar errores de alineación en el desensamblado parcial antes de implementar el vencimiento.

**Estado de pruebas externas:** el flujo de GitHub Actions incluye DNS, HTTPS y diagnóstico `buscarEquipo` con los cinco campos observados, pero una consulta de ejecuciones asociadas al commit previo no devolvió resultados; no hay prueba de conectividad satisfactoria confirmada. Ningún cambio se ha aplicado a Home Assistant.

## Cálculo exacto del umbral temporal en el APK (08/11/2026)

Inspección directa de los bytes de `classes2.dex` confirma **la misma fórmula en registro y acceso**:

| Flujo | Instrucciones DEX | Significado |
|---|---|---|
| Registro `LZ3/B;->invokeSuspend` | `2639286: 0b 02` | `move-result-wide v2`: milisegundos Unix devueltos por `Ly8/o;->a` |
| | `2639288: 17 04 80 d7 07 05` | `const-wide/32 v4, 0x0507d780` = **84.400.000 ms** |
| | `2639294: bb 42` | `add-long/2addr v2, v4` |
| | `2639296: 68 02 2c 5b` | `sput-wide v2, Ll7/I;->c:J` |
| Acceso `LZ3/D;->invokeSuspend` | `2640552: 0b 03` | `move-result-wide v3` |
| | `2640554: 17 05 80 d7 07 05` | `const-wide/32 v5, 0x0507d780` = **84.400.000 ms** |
| | `2640560: bb 53` | `add-long/2addr v3, v5` |
| | `2640562: 68 03 2c 5b` | `sput-wide v3, Ll7/I;->c:J` |

**Fórmula comprobada:** `Ll7/I.c = Instant.now().toEpochMilli() + 84_400_000`, aproximadamente **23 h 26 min 40 s**. Esta duración no es exactamente 24 horas; no redondearla ni sustituirla por 86.400.000 ms. La comprobación en `buscarClub` utiliza la clave almacenada mientras `ahora < Ll7/I.c`.

**Límite de la evidencia:** se conoce el umbral local utilizado para decidir si enviar `key`; no se ha probado que sea la caducidad efectiva de una sesión en el servidor ni cómo se renueva. No se han hecho solicitudes de registro ni cambios en Home Assistant.

## Versión enviada durante el registro (verificación DEX)

En `LZ3/B;->invokeSuspend`, offset `2638774`, se carga literalmente `5.0.42` mediante `const-string`. En `2638788` se invoca `Ld4/c;->b` con cuatro argumentos `String` y la continuación de corrutina; esta es la ruta que construye el formulario `registrar` en `dispositivo.ashx`. El valor `5.0.42` se encuentra en la preparación inmediata de la llamada y corresponde a la versión de la APK analizada.

**Precaución:** la evidencia confirma la constante de versión de esta compilación, no que sea un valor permanente ni que pueda utilizarse como sustituto de UID, plataforma o tipo de dispositivo. Sigue pendiente rastrear el origen de esos campos hasta sus productores y validar la petición con el servidor.

## Trazado de procedencia de argumentos del registro (DEX, 8-11-2026)

Se ha seguido la preparación de la llamada `LZ3/B;->invokeSuspend` → `Ld4/c;->b` (offset `2638788`), sin asumir valores por sus nombres ofuscados:

- En `2638692`, se lee `LN4/v;->b` desde un valor de `MutableStateFlow`; se prepara como argumento de la llamada.
- En `2638720` y `2638724`, se sigue `LN4/v;->c` → `LN4/a0;->e`; se prepara como otro argumento.
- En `2638752` y `2638756`, se sigue `LN4/v;->a` → `LN4/i1;->e`; se prepara como otro argumento.
- En `2638774`, se carga la constante `5.0.42`; en `2638788`, se ejecuta el `invoke-*/range` de `Ld4/c;->b`.

**Conclusión limitada:** los tres valores variables proceden del estado interno de la aplicación (`MutableStateFlow` y sus modelos), no de tres constantes inmediatas en la llamada. La asignación inequívoca de cada cadena a `uid`, `plataforma` y `tipo_dispositivo` exige seguir los registros hasta la construcción del formulario en `Ld4/c;->b` y rastrear quién rellena esos modelos. No se deben usar `LN4/v`, `LN4/a0` o `LN4/i1` como nombres semánticos de campos.

## Verificación de registros en llamada `registrar` (DEX)

Se ha comprobado el tramo de bytes de `classes2.dex` inmediatamente anterior al `invoke-range` de `Ld4/c;->b`:

| Offset DEX | Bytes | Interpretación |
| --- | --- | --- |
| 2638774 | `1a 05 5c 21` | `const-string v5, "5.0.42"` |
| 2638778 | `07 32` | `move-object v2, v3` |
| 2638780 | `07 43` | `move-object v3, v4` |
| 2638782 | `07 54` | `move-object v4, v5` |
| 2638784 | `08 05 2d 00` | `move-object/from16 v5, v45` (continuación) |
| 2638788 | `74 06 cc 6a 00 00` | `invoke-virtual/range {v0..v5}, Ld4/c;->b` |

La firma de `Ld4/c;->b` tiene **cuatro cadenas y una continuación**. En una invocación de instancia `v0` es el receptor, `v1..v4` son las cuatro cadenas y `v5` es la continuación. Por tanto, **la versión `5.0.42` es inequívocamente el cuarto parámetro de cadena (`v4`)**. Las otras tres cadenas son `v1`, `v2` y `v3`, cuyo origen exacto sigue pendiente de seguir hacia atrás. Esta comprobación evita confundir el orden de parámetros de registro.

## Asociación inequívoca entre argumentos y campos HTTP (DEX)

La función `Lc4/c;->b` construye el formulario de `registrar` con estas instrucciones:

| Offset | Instrucción DEX | Campo HTTP | Valor en registro |
| --- | --- | --- | --- |
| 2701898–2701904 | `const-string "uid"; move-object v12,v14; append` | `uid` | `v14` |
| 2701910–2701916 | `const-string "plataforma"; move-object v12,v15; append` | `plataforma` | `v15` |
| 2701922–2701930 | `const-string "tipo_dispositivo"; move-object/from16 v12,v16; append` | `tipo_dispositivo` | `v16` |
| 2701936–2701944 | `const-string "version"; move-object/from16 v12,v17; append` | `version` | `v17` |

Por la disposición de los registros de parámetros de `Lc4/c;->b`, los cuatro argumentos de cadena del llamador corresponden, **en orden**, a `uid`, `plataforma`, `tipo_dispositivo` y `version`. Esto resuelve la correspondencia posicional, pero **no** el origen ni los valores concretos de las primeras tres cadenas. Para resolverlos hay que rastrear los productores de los valores de `StateFlow` que llegan a `LZ3/B;->invokeSuspend`; no se deben sustituir por cadenas genéricas ni por un UUID aleatorio sin evidencia.

## Candidatos a generación del UID: inventario de cadenas DEX (8-11-2026)

Se inspeccionó directamente la tabla `string_ids` de `classes2.dex` de la APK 5.0.42. Contiene las cadenas `randomUUID` (índice 45221), `randomUUID().toString()` (45222), `android_id` (31811), `firebaseInstallations` (35494), `dispositivoRegistradoDbFBM` (34560) e `idDispositivoDbFBM` (39714).

**Importante:** la presencia de esas cadenas **no demuestra** que ninguna sea la fuente del `uid` enviado a `dispositivo.ashx`. Firebase y Android ID pueden pertenecer a bibliotecas incluidas en la APK; `idDispositivoDbFBM` puede ser un identificador recibido del servidor y no el UID local. La siguiente comprobación es buscar las referencias de código a estas cadenas y rastrear los valores hasta `LN4/v` y `LZ3/B;->invokeSuspend`. No usar UUID aleatorios ni Android ID sin ese enlace.

## Referencias directas a candidatos de UID en classes2.dex (análisis local)

Se ha buscado la instrucción DEX `const-string` (`0x1a`) para los índices de cadenas identificados previamente. Este barrido es **de candidatos**: cada coincidencia debe comprobarse contra los límites reales de instrucciones de un método.

| Cadena | Índice `string_ids` | Offsets candidatos |
| --- | ---: | --- |
| `android_id` | 31811 | 2641778, 2715090, 3206456, 3215480, 3225914, 3862812 |
| `randomUUID().toString()` | 45222 | 5339440 |
| `dispositivoRegistradoDbFBM` | 34560 | 2642502, 2643134 |
| `idDispositivoDbFBM` | 39714 | 2640026, 2642476, 2643176, 2659668 |
| `randomUUID` | 45221 | ninguna referencia directa `const-string` encontrada |
| `firebaseInstallations` | 35494 | ninguna referencia directa `const-string` encontrada |

**Pista prioritaria:** `android_id` aparece en `2641778`, próximo al bloque de inicialización de dispositivo, y los nombres de persistencia `dispositivoRegistradoDbFBM` e `idDispositivoDbFBM` aparecen en `2642xxx`. La proximidad por sí sola no demuestra flujo de datos ni permite afirmar que `uid = ANDROID_ID`. Debemos desensamblar el método propietario del offset `2641778` y seguir el resultado de `Settings.Secure.getString` (si existe) hasta el argumento `uid` de `Ld4/c;->b`. **No enviar todavía solicitudes con un identificador supuesto.**

## Descarte de falsos positivos de UID por método propietario (8-11-2026)

Se ha cruzado cada offset candidato con los `code_item` de **45.403 métodos** de `classes2.dex`, usando la tabla de clases y las posiciones reales de código. Esto permite distinguir código de FBM de bibliotecas externas:

| Referencia | Método propietario | Interpretación |
| --- | --- | --- |
| `android_id` @2641778 | `LZ3/H;->A` | **Código de inicialización FBM; candidato prioritario** |
| `android_id` @2715090 | `com/google/android/gms/internal/consent_sdk/C;->a` | Biblioteca Google Consent, no prueba UID FBM |
| `android_id` @3206456, 3215480, 3225914 | `com/google/android/gms/measurement/internal/zzav` | Biblioteca Google Analytics, no prueba UID FBM |
| `android_id` @3862812 | `com/qonversion/android/sdk/internal/EnvironmentProvider;->getDeviceId` | SDK Qonversion, no prueba UID FBM |
| `randomUUID().toString()` @5339440 | `okhttp3/MultipartBody$Builder;-><init>` | **Descartado como evidencia de UID FBM:** identificador interno de multipart |
| `dispositivoRegistradoDbFBM`, `idDispositivoDbFBM` @2642476–2643176 | `LZ3/H;->e` y `LZ3/H;->m` | Persistencia propia FBM; relevante para ciclo de vida |
| `idDispositivoDbFBM` @2640026 | `LZ3/D;->invokeSuspend` | Acceso de dispositivo |
| `idDispositivoDbFBM` @2659668 | `LZ3/u;->invokeSuspend` | Otra lectura propia de FBM |

**Resultado:** cinco de las seis referencias a `android_id` son de bibliotecas externas; la única candidata de código FBM es `LZ3/H;->A`. El candidato `randomUUID().toString()` pertenece a OkHttp y no debe usarse para generar UID. El siguiente paso es analizar las instrucciones de `LZ3/H;->A` y los lugares que consumen su valor. Este análisis de pertenencia a método **no demuestra aún** que `android_id` sea el UID del formulario de registro.

## UID confirmado mediante flujo de datos DEX (8-11-2026)

Se desensamblaron instrucciones **alineadas** de los métodos `LZ3/H;->A`, `LN4/v;-><init>` y `LZ3/B;->invokeSuspend` del APK 5.0.42:

1. `LZ3/H;->A` en offset `2641778` carga `"android_id"`; en `2641782` invoca `Landroid/provider/Settings$Secure;->getString` con `ContentResolver` y esa cadena. El resultado se conserva en `v2`.
2. En `2641888` se invoca `LN4/v;-><init>` con receptor `v0` y tres argumentos `v1`, `v2`, `v3`.
3. El constructor `LN4/v;-><init>` escribe esos argumentos en los campos `a`, `b` y `c`, respectivamente (offsets `1917526`, `1917530`, `1917534`). **Por tanto, `LN4/v;->b` contiene el Android ID leído.**
4. En el registro `LZ3/B;->invokeSuspend`, offset `2638692`, se lee `LN4/v;->b`. La llamada de registro `Ld4/c;->b` en `2638788` utiliza ese valor como primer argumento de cadena, que la construcción del formulario mapea a `uid`.

**Conclusión:** para la APK Android 5.0.42, el `uid` de registro procede de `Settings.Secure.ANDROID_ID`. No es un UUID aleatorio ni el `idDispositivo` que devuelve el servidor. Es un identificador del dispositivo/entorno Android, y no debe inventarse ni reutilizarse entre usuarios. El código HA no puede obtener automáticamente el Android ID de un teléfono: necesitaría un método legítimo de provisión o un mecanismo de registro alternativo contrastado.

Otros dos parámetros: `LZ3/H;->A` construye una cadena con `"Android "` y `Build.VERSION.RELEASE` para el objeto `LN4/a0`, y selecciona un valor de `LN4/i1` para tipo de dispositivo. En `LZ3/B;->invokeSuspend` se leen respectivamente `LN4/v;->c -> LN4/a0;->e` (segundo argumento, `plataforma`) y `LN4/v;->a -> LN4/i1;->e` (tercero, `tipo_dispositivo`). El valor concreto de `LN4/i1;->e` requiere revisar la inicialización del enum.

## Tipo de dispositivo y plataforma: valores confirmados (DEX 5.0.42)

Se ha desensamblado el inicializador del enum `LN4/i1;-><clinit>` (offset 1911840) y el método de identificación `LZ3/H;->A` (offset 2641712):

- Enum `PHONE` → cadena de formulario **`mobile`**, inicializado en offsets 1911844–1911860.
- Enum `TABLET` → cadena **`tablet`**, inicializado en 1911868–1911884.
- Enum `OTRO` → cadena **`otro`**, inicializado en 1911892–1911908.
- `LZ3/H;->A` lee `Resources.getConfiguration().screenLayout` y compara una máscara con `0x258` (offsets 2641732–2641748). Según la rama, selecciona `TABLET` (2641752) o `PHONE` (2641758). Para la ruta de teléfono, el valor enviado en `tipo_dispositivo` es por tanto **`mobile`**.
- En 2641804 carga **`Android `** y lo concatena con `Build.VERSION.RELEASE`; esta cadena alimenta el objeto de plataforma y posteriormente el segundo argumento `plataforma` del registro. Por ejemplo, la forma es `Android <versión del sistema>`, no el literal `Android` aislado.

**Campos del registro para la ruta teléfono Android de la APK 5.0.42:**
`uid = Settings.Secure.ANDROID_ID` del entorno Android;
`plataforma = "Android " + Build.VERSION.RELEASE`;
`tipo_dispositivo = "mobile"`;
`version = "5.0.42"`.

Estos son valores del protocolo Android observado, **no credenciales de acceso**. Sigue pendiente validar el registro real y establecer una provisión legítima del Android ID desde un dispositivo autorizado, sin inventarlo ni registrar uno ajeno.

## Identidad independiente experimental (08/11/2026)

El diagnóstico permite crear un UID aleatorio propio de 16 dígitos hexadecimales y guardarlo en un archivo local. No es el ANDROID_ID de la aplicación ni se afirma que el servidor acepte este formato. La plataforma Android y la versión 5.0.42 son los valores observados en la APK, usados aquí como perfil experimental, no una descripción del equipo que ejecuta el script. La aceptación de clientes independientes y los nombres JSON de respuesta siguen sin validar.

Desde la raíz del repositorio en PowerShell, usando una ruta privada fuera del repositorio:

```powershell
py -3.13 .\scripts\probar_registro_invitado.py --android-release 16
py -3.13 .\scripts\probar_registro_invitado.py --android-release 16 --identidad "$env:LOCALAPPDATA\fbm-identidad.json" --crear-identidad
# Solo cuando se desee probar un registro real:
py -3.13 .\scripts\probar_registro_invitado.py --android-release 16 --identidad "$env:LOCALAPPDATA\fbm-identidad.json" --enviar
```

El primer comando no escribe ni conecta. El segundo crea el archivo sin sobrescribirlo ni conectar. El tercero realiza un POST de registro: conserva el archivo para mantener la identidad y no lo compartas ni lo subas a Git. El archivo contiene un identificador, no una clave recibida del servicio; los permisos y copias de seguridad dependen del sistema. Una respuesta con ambos campos esperados no valida búsquedas ni acceso posterior. El diagnóstico no guarda la sesión; repetir el envío puede crear o modificar un registro remoto. No se ha realizado ninguna prueba real en este cambio. En caso de rechazo o respuesta inesperada no se muestran cuerpos ni identificadores.

### Resultado de la primera prueba independiente

El usuario ejecutó la creación local de identidad y después un envío explícito. El diagnóstico devolvió «Registro no validado», pero la versión utilizada agrupaba errores de identidad, transporte y formato; no permite determinar la causa ni si el servidor procesó la solicitud. No se conocen el estado HTTP ni la respuesta. La versión posterior distingue estado HTTP, fallo de conexión, JSON inválido o no objeto, y presencia válida de los dos campos previstos, sin imprimir valores ni cuerpo. Las pruebas automatizadas de estas clasificaciones usan respuestas simuladas; no demuestran aceptación del servidor. Repetir el registro es una petición nueva que podría crear o modificar un registro remoto.

### Segunda prueba independiente

En una segunda solicitud explícita, el usuario observó una respuesta JSON con `key` de texto no vacía, sin `idDispositivo` de texto no vacío y con un valor en `error` distinto de los valores que el diagnóstico consideraba vacíos. Esto no demuestra un error real: el significado y el tipo de `error` siguen sin verificarse. El diagnóstico posterior informa únicamente de presencia y tipo de campos concretos candidatos, sin mostrar sus valores. Aún no hay sesión validada ni prueba de búsqueda.

### Respuesta observada y marcador de error

En la siguiente solicitud explícita se observaron `key` e `id_dispositivo` como textos no vacíos; `idDispositivo` y `dispositivoId` estaban ausentes. El campo `error` era texto no vacío. La respuesta no se guardó, por lo que no es posible recuperar su valor. El diagnóstico reconoce ahora un conjunto limitado de marcadores literales comunes de `error` sin atribuirles significado; cualquier otro contenido permanece oculto. La presencia de estos campos o de un marcador no demuestra que la sesión sea válida. El extractor de producción permanece conservador hasta conocer el contrato.
