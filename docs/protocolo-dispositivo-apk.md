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
