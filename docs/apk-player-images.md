# APK photo-resolution evidence — Afición FBM 5.0.42

This is a technical, metadata-only record. **No player names, photo references, images, accounts, or credentials are included.**

## Source

User-provided split APK archive `Afición FBM-5.0.42-split-apks(2).zip`; inspected `base.apk/classes2.dex`. The source app is **com.indalweb.aficionFBM** (not affiliated with this project).

## Confirmed bytecode facts

1. Static field `Lcom/google/android/gms/internal/play_billing/r0;->a:Ljava/lang/String;` has its DEX encoded static value set to `https://appaficionfbm.gesdeportiva.es/imagenes.ashx`.
2. Method `LR4/o;->t` constructs an image URI using `?tipo=`, `&id=`, and the image type `jugador`. It loads the static URL field above as the base.
3. In the official model `JugadorEquipoDto`, `getFoto()` is passed into the app's `JugadorEquipo` model (`LX8/b;->f0`). Its `e` field is confirmed to be the `foto` field by the generated model's `toString`.
4. The roster renderer `LA9/j;->b` accesses `LJ5/g;->e` and invokes `LR4/o;->t` with this image reference.
5. Real metadata-only diagnostics from the FBM guest response show `Foto` is an opaque hex string containing UTF-16LE text, with an inner Base64-or-identifier form; its inner bytes **are not a recognized image**.

## Implementation decision

Do not decode `Foto` into a purported image, do not replace it with the player's sports ID and do not fabricate image contents. Send a strictly validated original `Foto` reference as the image `id` to the official image endpoint, with `tipo=jugador`. The integration restricts accepted references to bounded hex-encoded UTF-16LE strings that contain ASCII base64-or-identifier characters. The Lovelace card only renders this exact HTTPS host/path/query shape or verified inline images, with an image-error fallback.

## Limits and validation

This verifies the **URI construction in the APK**, not that each FBM player has a public photo or that requests succeed for all categories. Installation on the user's Home Assistant, a roster refresh, and visual confirmation are required before declaring the issue fixed. Do not paste private `Foto` references into issues or logs.

---

# Evidencia de resolución de fotos — APK Afición FBM 5.0.42

Documento técnico sin datos personales: no incluye nombres, fotografías, referencias de jugadores ni credenciales.

1. El campo estático DEX `Lcom/google/android/gms/internal/play_billing/r0;->a` contiene `https://appaficionfbm.gesdeportiva.es/imagenes.ashx`.
2. El método `LR4/o;->t` construye la solicitud con `?tipo=` y `&id=` para el tipo `jugador`.
3. `JugadorEquipoDto.getFoto()` se convierte al campo `foto` del modelo de la aplicación, que el componente visual pasa al método anterior.
4. Los diagnósticos reales indican que `Foto` es una referencia opaca hexadecimal UTF-16LE y no una imagen PNG/JPEG/WebP directamente decodificable.
5. Se conserva `Foto` sin alteraciones y se utiliza en la URL oficial únicamente si cumple una validación estricta. La tarjeta rechaza dominios no oficiales y oculta la miniatura cuando falla.

**Pendiente:** prueba visual en Home Assistant. No publicar referencias privadas, nombres ni fotos en registros o incidencias.
