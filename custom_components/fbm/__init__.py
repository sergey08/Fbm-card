"""FBM: infraestructura de integración y tarjeta.

No se consultan resultados hasta validar el acceso oficial a FBM.
"""
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import CARD_URL, DOMAIN


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
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "estado": "pendiente_validacion_api_oficial"
    }
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Eliminar el estado de la entrada."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
