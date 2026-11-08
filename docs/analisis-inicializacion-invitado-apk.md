# Análisis estático de inicialización invitada — Afición FBM 5.0.42

Fecha: 08/11/2026. **Fuente única: APK facilitado por el usuario** `Afición FBM-5.0.42-split-apks.zip` (SHA-256 `31ac162e717dd045870c3cbf1cb22f64e5ba3dedc93d31600c4e8acbf61df099`).

## Hallazgos comprobados en los artefactos del análisis DEX
- El paquete `base.apk` contiene `classes.dex` y `classes2.dex`.
- En `classes2.dex` hay referencias a `https://appaficionfbm.gesdeportiva.es/dispositivo.ashx`, `autenticar.ashx`, `v2/busqueda.ashx`, `v2/equipo.ashx`, `v2/categoria.ashx`, `v2/club.ashx` y rutas `v2/envivo/`.
- Se localizaron cadenas `&id_dispositivo=`, `&key=`, `&id_equipo=`, `&id_grupo=`, `&id_partido=` y `&tipo_fase=`. Son referencias de código, **no** una especificación confirmada de peticiones.
- El análisis de la rutina `LZ3/B;->invokeSuspend` observa una llamada a `Ld4/c;->b` cerca del desplazamiento DEX `2638788`. El método recibe **cuatro cadenas** y un parámetro de continuación de corrutina; en el mismo flujo aparece el literal de versión `5.0.42`. **No se ha probado todavía qué representa cada argumento**.
- Otra rutina `LZ3/D;->invokeSuspend` referencia `idDispositivoDbFBM`, la versión `5.0.42`, una llamada a `Ld4/c;->a` y los literales `key` y `dispositivoId`. Esto **sugiere** un flujo de inicialización o recuperación de identidad de dispositivo, pero no demuestra su semántica ni autoriza generar claves.

## Evidencias de trabajo
Artefactos locales previos: `fbm_apk_endpoints.json`, `fbm_apk_audit.json`, `fbm_analysis/init_call_signature.json`, `fbm_analysis/guest_next_summary.txt`. El desensamblado parcial contiene opcodes no interpretados: no inferir contratos HTTP a partir de ellos.

## Próximas comprobaciones
1. Inspeccionar las definiciones de `Ld4/c;->a` y `Ld4/c;->b` y la relación con `dispositivo.ashx` **sin extraer claves ni tokens**.
2. Determinar si la inicialización invitada utiliza un mecanismo público/documentado de registro de dispositivo.
3. Confirmar mediante petición legítima el esquema real de búsqueda y de jornadas, y revisar las condiciones de acceso externo.
4. Conectar el adaptador a `FBMQueries` solo cuando haya respuesta verificable y acceso permitido.

**Estado:** análisis estático parcial; ninguna consulta deportiva real validada. Sin acceso confirmado, sin datos simulados y sin modificar `main`.
