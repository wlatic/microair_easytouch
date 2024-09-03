from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import logging
import aiohttp
import asyncio

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_PORT, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class MyClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for My Climate Integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the IP and port
            ip = user_input[CONF_IP_ADDRESS]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            
            if await self._test_api_connection(ip, port):
                # Add entities key to user_input with an empty list if not provided
                if "entities" not in user_input:
                    user_input["entities"] = []  # Ensure entities key exists

                return self.async_create_entry(title="My Climate Integration", data=user_input)
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

    async def _test_api_connection(self, ip, port):
        """Test if the provided IP and port can connect to the API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://{ip}:{port}/read') as response:
                    return response.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError):
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
        self.entity_id = None

    async def async_step_init(self, user_input=None):
        """Show the list of entities to select for configuration."""
        entities = self.config_entry.data.get("entities", [])
        
        if not entities:
            _LOGGER.error("No entities found in configuration data. Ensure entities are added during configuration.")
            return self.async_abort(reason="no_entities")

        entity_list = {entity["id"]: entity["name"] for entity in entities}

        if user_input is not None:
            # Save the selected entity ID and move to the next step
            self.entity_id = user_input["entity"]
            return await self.async_step_entity_options()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("entity"): vol.In(entity_list)
            }),
        )

    async def async_step_entity_options(self, user_input=None):
        """Manage the options for the selected entity."""
        entity_settings = self.config_entry.options.get("entity_settings", {})
        current_entity_settings = entity_settings.get(self.entity_id, {})

        if user_input is not None:
            # Save the user-selected options for the specific entity
            entity_settings[self.entity_id] = user_input
            self.hass.config_entries.async_update_entry(
                self.config_entry, options={"entity_settings": entity_settings}
            )
            return self.async_create_entry(title="", data={})

        # Default options schema for per-entity settings
        options_schema = vol.Schema({
            vol.Optional("enabled_modes", default=current_entity_settings.get("enabled_modes", ["heat", "cool", "fan_only"])): cv.multi_select(["heat", "cool", "fan_only"])
        })

        return self.async_show_form(step_id="entity_options", data_schema=options_schema)
