"""FBM: infraestructura de integración y tarjeta.

No se consultan resultados hasta validar el acceso oficial a FBM.
"""
from pathlib import Path
import logging

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import CARD_URL, DOMAIN


async def _async_register_lovelace_resource(hass: HomeAssistant) -> bool:
    """Registrar la tarjeta en recursos Lovelace cuando el modo storage lo permita.

    En dashboards YAML no se modifican archivos del usuario.
    """
    lovelace = hass.data.get(LOVELACE_DOMAIN)
    resources = getattr(lovelace, "resources", None)
    if resources is None:
        return False
    try:
        await resources.async_load()
        if any(item.get("url", "").split("?")[0] == CARD_URL for item in resources.async_items()):
            return True
        await resources.async_create_item({"res_type": "module", "url": CARD_URL})
        return True
    except (AttributeError, KeyError, TypeError, ValueError) as err:
        _LOGGER.warning("No se pudo registrar el recurso FBM automáticamente: %s", err)
        return False



async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Servir la tarjeta empaquetada en la misma instalación."""
    card_path = Path(__file__).parent / "www" / "fbm-card.js"
    if card_path.is_file():
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Preparar la integración sin afirmar que existe conexión a la API."""
    recurso_registrado = await _async_register_lovelace_resource(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "estado": "pendiente_validacion_api_oficial",
        "recurso_lovelace_registrado": recurso_registrado,
    }
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Eliminar el estado de la entrada."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
