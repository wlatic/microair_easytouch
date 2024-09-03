from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
import aiohttp
import asyncio

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_PORT, DEFAULT_PORT

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
                return self.async_create_entry(title="My Climate Integration", data=user_input)
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_IP_ADDRESS): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
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
