"""FBM: infraestructura de integración y tarjeta.

No se consultan resultados hasta validar el acceso oficial a FBM.
"""
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store

from .const import CARD_URL, DOMAIN
from .query_cache import QueryCache
from .independent_identity import IndependentIdentityStore
from .independent_client import IndependentClient
from .followed_groups_store import FollowedGroups
from .competition_archive import CompetitionArchive
from .websocket import async_register_commands

_LOGGER = logging.getLogger(__name__)


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
    except (AttributeError, KeyError, TypeError, ValueError, OSError) as err:
        _LOGGER.warning("No se pudo registrar el recurso FBM automáticamente: %s", err)
        return False



async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Servir la tarjeta empaquetada en la misma instalación."""
    card_path = Path(__file__).parent / "www" / "fbm-card.js"
    if not card_path.is_file():
        _LOGGER.error("Falta la tarjeta empaquetada FBM: %s", card_path)
        return False
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
    )
    async_register_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Preparar la integración sin afirmar que existe conexión a la API."""
    recurso_registrado = await _async_register_lovelace_resource(hass)
    identity_storage = Store(hass, 1, f"{DOMAIN}.identity.{entry.entry_id}", private=True, atomic_writes=True)

    async def identity_file_exists() -> bool:
        return await hass.async_add_executor_job(Path(identity_storage.path).exists)

    identity_manager = IndependentIdentityStore(identity_storage, async_exists=identity_file_exists)
    recovery_storage = Store(hass, 1, f"{DOMAIN}.recovery.{entry.entry_id}", private=True, atomic_writes=True)
    client = IndependentClient(identity_manager, recovery_store=recovery_storage)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "estado": "pendiente_validacion_api_oficial",
        "recurso_lovelace_registrado": recurso_registrado,
        "cache": QueryCache(),
        "cache_consultas": QueryCache(ttl_seconds=300, max_entries=128),
        "identidad_independiente": identity_manager,
        "cliente_independiente": client,
        # Store is initialized lazily only after an explicitly selected group.
        # No requests, new groups or filesystem mutations are triggered here.
        "grupos_sqlite_path": hass.config.path(f"fbm_groups_{entry.entry_id}.sqlite"),
        "grupos_store_factory": FollowedGroups,
        "competitions_sqlite_path": hass.config.path(f"fbm_competitions_{entry.entry_id}.sqlite"),
        "competitions_archive_factory": CompetitionArchive,
    }
    # Existing-device access only; no registration or identity replacement.
    restored = await client.async_restore()
    _LOGGER.info("FBM saved guest session restored: %s", restored)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    # Automatic network requests are disabled by default and require
    # explicit consent in the native Configure → Automatic menu.
    auto_groups = entry.options.get("auto_groups") is True
    auto_players = entry.options.get("auto_players") is True
    hass.data[DOMAIN][entry.entry_id]["auto_sync_flags"] = (
        auto_groups, auto_players)
    if auto_groups:
        from .competition_auto_sync import CompetitionAutoUpdater
        service = CompetitionAutoUpdater(
            hass, entry.entry_id, client,
            hass.data[DOMAIN][entry.entry_id]["competitions_sqlite_path"],
            CompetitionArchive)
        await service.async_start(groups=True, players=auto_players)
        hass.data[DOMAIN][entry.entry_id]["auto_updater"] = service

    async def _options_updated(hass, updated_entry):
        # Following/unfollowing and manual refresh also save OptionsFlow,
        # but they must not interrupt an existing FBM guest session or cards.
        previous = hass.data.get(DOMAIN, {}).get(
            updated_entry.entry_id, {}).get("auto_sync_flags")
        desired = (
            updated_entry.options.get("auto_groups") is True,
            updated_entry.options.get("auto_players") is True)
        if previous != desired:
            await hass.config_entries.async_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Eliminar el estado de la entrada."""
    state = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if state is not None:
        updater = state.get("auto_updater")
        if updater is not None:
            await updater.async_stop()
        await state["cliente_independiente"].async_disconnect()
        state["cache_consultas"].clear()
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
