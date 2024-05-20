import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class MicroAirEasyTouchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            zones, api_error = await self.verify_api_connection(user_input)

            if api_error:
                errors["base"] = api_error
                _LOGGER.error(f"API error: {api_error}")
            else:
                return self.async_create_entry(
                    title=user_input["host"],
                    data={
                        "host": user_input["host"],
                        "port": user_input["port"],
                        "zones": zones,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("host", description="Host"): str,
                    vol.Required("port", description="Port", default=5000): int,
                }
            ),
            errors=errors,
        )

    async def verify_api_connection(self, user_input):
        try:
            _LOGGER.info("Testing API connection to %s", user_input["host"])
            url = f"http://{user_input['host']}:{user_input['port']}/read"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=45) as response:
                    if response.status != 200:
                        return None, "api_connection_error"
                    output = await response.json()
                    zones = {str(zone["Zone"]): zone for zone in output}
                    return zones, None
        except Exception as e:
            _LOGGER.exception("Unexpected exception for %s", user_input["host"])
            return None, "unknown"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MicroAirEasyTouchOptionsFlowHandler(config_entry)

class MicroAirEasyTouchOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        zones = self.config_entry.data.get("zones", {})
        options_schema = vol.Schema({})

        for zone_id, zone_data in zones.items():
            zone_name = zone_data.get("Label", f"Zone {zone_id}")
            options_schema = options_schema.extend(
                {
                    vol.Optional(
                        f"zone_{zone_id}_hvac_modes",
                        description=f"HVAC Modes for {zone_name}",
                        default=self.config_entry.options.get(f"zone_{zone_id}_hvac_modes", ["heat", "cool", "fan_only", "off"]),
                    ): cv.multi_select({"heat": "Heat", "cool": "Cool", "fan_only": "Fan Only", "off": "Off"}),
                }
            )

        return self.async_show_form(step_id="init", data_schema=options_schema)
