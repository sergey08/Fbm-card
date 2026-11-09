# Instalación beta de FBM Card mediante HACS/Marketplace

## Objetivo

Probar el código de la rama `dev` mediante una publicación *pre-release* instalable desde HACS/Marketplace. Sin fusionar `main`, eliminar la integración existente, registrar otra identidad FBM, cambiar equipos ni sustituir manualmente archivos de HA.

## 1. Publicación GitHub (una sola vez por beta)

1. Comprobar que GitHub Actions ha terminado en verde para el HEAD de `dev`.
2. Abrir [Nueva publicación](https://github.com/sergey08/Fbm-card/releases/new).
3. Seleccionar **Choose a tag → Create new tag** y escribir `v0.1.0b1`.
4. En **Target** elegir explícitamente **`dev`**, nunca `main`.
5. Título: `FBM Card 0.1.0b1 — prueba de calendarios y jugadores`.
6. Marcar **Set as a pre-release**. No marcar «latest»/versión estable.
7. Notas de publicación: las búsquedas y clasificaciones ya existentes permanecen; las consultas de calendario, plantilla, ficha y estadísticas son experimentales y requieren validación real con la identidad FBM existente. Nunca publicar tokens, nombres de menores ni JSON real.
8. Publicar solo después de la CI correcta. Confirmar que el tag creado apunta al commit de `dev` que contiene `custom_components/fbm/manifest.json` con `version: 0.1.0b1`.

Si el formulario presenta un destino distinto de `dev`, **no publicar** hasta corregirlo. No adjuntar ZIP especial: la integración sigue el esquema estándar `custom_components/fbm`.

## 2. HACS/Marketplace en Home Assistant

1. Comprobar que el repositorio `https://github.com/sergey08/Fbm-card` figura como **Integration**. Si no aparece, añadirlo como *Custom repository* de tipo integración.
2. Abrir la ficha de FBM Card. Activar **Show beta versions** o equivalente, cuando exista esa preferencia.
3. En **Download/Redownload** → **Need a different version?**, elegir `v0.1.0b1`. **No elegir la rama por defecto/main**.
4. Antes de instalar, guardar copia de seguridad de Home Assistant y comprobar que se conserva `/config/.storage`. HACS puede sustituir el directorio completo `custom_components/fbm` en una actualización; no almacenar datos persistentes dentro.
5. Descargar, comprobar configuración de Home Assistant y reiniciar cuando HACS lo indique.
6. Verificar en Ajustes → Dispositivos y servicios que la entrada **FBM (modo invitado)** existente permanece cargada, que los equipos favoritos siguen ahí y que no se ha creado ninguna identidad o entrada duplicada.
7. En la tarjeta, usar búsqueda y clasificación como prueba de regresión, luego consulta manual de jugadores; si falla, recopilar solo error anonimizado.

## 3. Validación real y reversión

- Primer diagnóstico de un equipo oficial ya configurado: WebSocket `fbm/team/schedule_probe` (solo administrador), que devuelve exclusivamente la estructura y no datos personales.
- Después `fbm/team/players`. Si hay una plantilla válida, `fbm/player/detail`. Las estadísticas `fbm/player/stats` solo si la ficha demuestra los cuatro IDs oficiales y los datos están disponibles.
- Si falla la beta: desde HACS/Marketplace volver a descargar la versión anterior elegida, reiniciar, revisar la integración y conservar `.storage`. Restaurar la copia de seguridad si la actualización rompe la carga.
- La beta no activa seguimiento persistente ni sincronización automática de grupos. `main` permanece intacta.

## Limitaciones

La presencia de modelos Kotlin en la APK FBM 5.0.42 no equivale a confirmar el JSON de producción ni la disponibilidad de estadísticas para menores. Las pruebas CI usan simulaciones. La publicación pre-release y la instalación en HA deben confirmarse antes de afirmar que la beta está disponible en HACS.
