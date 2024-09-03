import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_PORT, DEFAULT_PORT
from .api_client import MyClimateAPI

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the My Climate Integration component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up My Climate Integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize the API client
    api_client = MyClimateAPI(
        entry.data[CONF_IP_ADDRESS],
        entry.data.get(CONF_PORT, DEFAULT_PORT)
    )
    hass.data[DOMAIN][entry.entry_id] = api_client

    # Add the climate platform
    await hass.config_entries.async_forward_entry_setup(entry, "climate")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["climate"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
