from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import logging
import aiohttp
import asyncio

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_PORT, DEFAULT_PORT
from .api_client import MyClimateAPI

_LOGGER = logging.getLogger(__name__)

class MyClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for My Climate Integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            ip = user_input[CONF_IP_ADDRESS]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            
            api_client = MyClimateAPI(ip, port)
            if await self._test_api_connection(api_client):
                # Fetch initial status and create placeholder entities
                status = await api_client.read_status()
                if status and "Zones" in status:
                    entities = []
                    for zone in status["Zones"]:
                        entity_id = f"climate.zone_{zone['Zone']}"
                        entities.append({"id": entity_id, "name": f"Climate Zone {zone['Zone']}"})
                    
                    user_input["entities"] = entities
                    return self.async_create_entry(title="My Climate Integration", data=user_input)
                else:
                    errors["base"] = "no_zones"
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_IP_ADDRESS): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int
            }),
            errors=errors,
        )

    async def _test_api_connection(self, api_client):
        """Test if the provided API client can connect to the device."""
        try:
            status = await api_client.read_status()
            return status is not None
        except Exception:
            return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return MyClimateOptionsFlowHandler(config_entry)


class MyClimateOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for the custom component."""
        errors = {}
        current_config = self.config_entry.data
        current_options = self.config_entry.options

        if user_input is not None:
            # Validate user input and save options
            new_options = dict(current_options)
            new_options.update(user_input)
            return self.async_create_entry(title="", data=new_options)

        # Prepare the options form
        entities = current_config.get("entities", [])
        options_schema = {}

        for entity in entities:
            entity_id = entity["id"]
            current_enabled_modes = current_options.get(f"enabled_modes_{entity_id}", ["heat", "cool", "fan_only"])
            options_schema[vol.Optional(f"enabled_modes_{entity_id}", default=current_enabled_modes)] = cv.multi_select(
                {"heat": "Heat", "cool": "Cool", "fan_only": "Fan Only"}
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema),
            errors=errors,
        )
