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
