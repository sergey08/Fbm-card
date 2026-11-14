# Publicación en el catálogo oficial de HACS

## Estado

FBM Card se instala actualmente como repositorio personalizado de tipo **Integración**. Su inclusión en el catálogo por defecto de HACS todavía **no está aprobada ni solicitada**.

Repositorio: `sergey08/Fbm-card`  
Categoría prevista: `integration` (incluye `custom_components/fbm`, además de tarjetas Lovelace).

## Requisitos de admisión

1. Repositorio público y accesible como integración personalizada: comprobado.
2. Estructura de integración única `custom_components/fbm/`: comprobada.
3. Marca local en `custom_components/fbm/brand/`: presente.
4. Workflow `hacs/action@main` para categoría `integration` sin exclusiones: añadido; resultado pendiente.
5. Workflow `home-assistant/actions/hassfest@master`: añadido; resultado pendiente.
6. **Licencia del código**: propietario eligió MIT el 14/11/2026; archivo `LICENSE` incorporado y aclaración de atribuciones/terceros en README. La titularidad y procedencia de todos los componentes externos no se acreditan por esta declaración.
7. Crear una **nueva release posterior a las validaciones aprobadas**.
8. Presentar PR desde un fork personal de `hacs/default` (rama `master`) añadiendo la entrada exacta `sergey08/Fbm-card` en `integration`.
9. Esperar revisión/CI y merge del equipo HACS. No afirmar inclusión oficial antes de su aceptación.

## Notas

- VE Builder Card y Snapmaker U1 Card figuran en `hacs/default/plugin`. FBM Card corresponde a `integration`, no `plugin`.
- Mantener el aviso de proyecto **no oficial** respecto a la Federación de Baloncesto de Madrid.
- Conservar el mecanismo de repositorio personalizado en README hasta que la inclusión se confirme realmente. Después, actualizar la guía para instalación directa.
- Consultar https://hacs.dev/docs/publish/include/ y https://www.hacs.dev/docs/publish/integration/ para los requisitos vigentes.

## Resultados de la primera ejecución de los validadores (14/11/2026)

- [HACS/Hassfest run #43635599340](https://github.com/sergey08/Fbm-card/actions/runs/43635599340): inicialmente fallaron ambas comprobaciones.
- **Hassfest:** error de orden de claves en `manifest.json`, corregido en la rama. Aviso no bloqueante sobre ausencia de `CONFIG_SCHEMA` para `async_setup` (revisar posteriormente sin romper la integración).
- **HACS:** faltan un archivo `LICENSE` en el repositorio y temas válidos (*repository topics*) en los metadatos de GitHub. El resto de las validaciones pasó; el comprobador de marca local pasó. Aviso de categorías de integración no bloqueante.
- La elección de una licencia de código requiere decisión del propietario y revisar la procedencia de las fuentes. No suprimir la validación `license` con `ignore` para simular cumplimiento.
- Los temas del repositorio se deben añadir desde **GitHub → About → Edit (engranaje) → Topics**; por ejemplo `home-assistant`, `hacs` y `basketball`, comprobando los requisitos exactos del catálogo. Este conector no permite escribir temas.
- Después de corregir estos dos bloqueos y obtener ambas validaciones verdes, emitir nueva release estable y preparar una PR a `hacs/default`.

## Auditoría inicial de procedencia (14/11/2026)

- Archivos inspeccionados: estructura completa de repositorio (Python, JS, pruebas, scripts, assets y docs), `fbm-card.js`, `custom_components/fbm/__init__.py`, `device_protocol.py`, `image_references.py`, `docs/fuente-unica-aficion-fbm.md`, `docs/analisis-inicializacion-invitado-apk.md`, `docs/escudos-oficiales-dev.md` y `docs/solicitud-acceso-fbm.md`.
- Implementación específica de Home Assistant en `custom_components/fbm`, frontend `fbm-card.js` empaquetado en `www/` y pruebas propias. **No se ha demostrado procedencia ajena del código inspeccionado**, pero esta revisión es inicial y **no constituye una auditoría exhaustiva de cada línea ni una garantía de titularidad**.
- La documentación describe inspección estática de la APK Afición FBM 5.0.42 para identificar endpoints, nombres de campos y secuencias de comunicación. No confundir la interoperabilidad ni los contratos observados con autorización del proveedor, titularidad del protocolo o derecho a copiar código de la APK. No se ha acreditado permiso expreso de la FBM/Gesdeportiva para reutilización por terceros.
- Los escudos, fotografías y datos de equipos se obtienen o referencian en el servicio oficial y **no quedan licenciados por el MIT** del proyecto. Capturas de pantalla pueden mostrar esos recursos, que mantienen los derechos de sus propietarios.
- La licencia MIT incorporada tiene `Copyright (c) 2026 sergey08` para el código propio. No agregar copyright a recursos ajenos. La publicación bajo MIT fue solicitada expresamente por el propietario en esta conversación.
- Pendiente legal/técnico separado de HACS: confirmar condiciones de API, límites, uso de imágenes y datos con los titulares si no existe licencia pública aplicable.
