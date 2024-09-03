import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)

class MyClimateAPI:
    """API client for interacting with the climate devices."""

    def __init__(self, ip_address, port):
        """Initialize the API client."""
        self._base_url = f"http://{ip_address}:{port}"
        self._session = aiohttp.ClientSession()

    async def read_status(self):
        """Fetch the current status from the device."""
        try:
            async with self._session.get(f"{self._base_url}/read") as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching status: %s", err)
            return None

    async def send_command(self, zone, changes):
        """Send a control command to the device."""
        payload = {
            "zone": zone,
        }
        
        if "power" in changes:
            payload["power"] = changes["power"]
        if "mode" in changes:
            payload["mode"] = changes["mode"]
        if "temperature" in changes:
            payload["temperature"] = changes["temperature"]
        if "fan" in changes:
            payload["fan"] = changes["fan"]

        try:
            async with self._session.post(f"{self._base_url}/write", json=payload) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error sending command: %s", err)
            return None

    async def close(self):
        """Close the HTTP session."""
        await self._session.close()
