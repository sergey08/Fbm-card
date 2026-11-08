"""Configuración local de FBM, sin cuentas ni credenciales externas."""
from homeassistant import config_entries
from .const import DOMAIN


class FBMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Crear una única configuración FBM en Home Assistant."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Configurar en modo invitado, sin inventar credenciales."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="FBM (modo invitado)", data={})
        return self.async_show_form(step_id="user")
