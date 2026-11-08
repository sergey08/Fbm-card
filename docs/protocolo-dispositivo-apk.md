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
