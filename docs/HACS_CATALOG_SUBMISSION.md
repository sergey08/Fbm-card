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
6. **Licencia del código**: no hay archivo `LICENSE` en la raíz; pendiente resolver con el propietario. No elegir ni aplicar una licencia sin autorización.
7. Crear una **nueva release posterior a las validaciones aprobadas**.
8. Presentar PR desde un fork personal de `hacs/default` (rama `master`) añadiendo la entrada exacta `sergey08/Fbm-card` en `integration`.
9. Esperar revisión/CI y merge del equipo HACS. No afirmar inclusión oficial antes de su aceptación.

## Notas

- VE Builder Card y Snapmaker U1 Card figuran en `hacs/default/plugin`. FBM Card corresponde a `integration`, no `plugin`.
- Mantener el aviso de proyecto **no oficial** respecto a la Federación de Baloncesto de Madrid.
- Conservar el mecanismo de repositorio personalizado en README hasta que la inclusión se confirme realmente. Después, actualizar la guía para instalación directa.
- Consultar https://hacs.dev/docs/publish/include/ y https://www.hacs.dev/docs/publish/integration/ para los requisitos vigentes.
