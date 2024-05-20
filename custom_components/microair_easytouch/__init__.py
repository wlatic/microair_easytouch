import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the MicroAir EasyTouch integration."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up MicroAir EasyTouch from a config entry."""
    _LOGGER.info("Setting up MicroAir EasyTouch integration")
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "climate"))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info("Unloading MicroAir EasyTouch integration")
    return await hass.config_entries.async_forward_entry_unload(entry, "climate")
