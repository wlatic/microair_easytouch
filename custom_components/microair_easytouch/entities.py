from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
)
from homeassistant.const import TEMP_FAHRENHEIT, ATTR_TEMPERATURE

import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

class MicroAirEasyTouchClimateEntity(ClimateEntity):

    def __init__(self, entry_id, zone_id, zone_data, host):
        self._entry_id = entry_id
        self._zone_id = zone_id
        self._zone_data = zone_data
        self._host = host
        self._name = f"MicroAir Zone {zone_id}"

    @property
    def unique_id(self):
        return f"{self._entry_id}_{self._zone_id}"

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return TEMP_FAHRENHEIT

    @property
    def target_temperature(self):
        return self._zone_data.get('Cooling Set Point (°F)')

    @property
    def current_temperature(self):
        return self._zone_data.get('Inside Temperature (°F)')

    @property
    def hvac_mode(self):
        mode = self._zone_data.get('Mode', 'Off')
        if mode == 'Off':
            return HVAC_MODE_OFF
        elif mode == 'Heating':
            return HVAC_MODE_HEAT
        elif mode == 'Cooling':
            return HVAC_MODE_COOL
        return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL]

    @property
    def fan_mode(self):
        return self._zone_data.get('Fan Setting')

    @property
    def fan_modes(self):
        return ['Auto', 'Low', 'Medium', 'High']

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            self._zone_data['Cooling Set Point (°F)'] = kwargs[ATTR_TEMPERATURE]
            _LOGGER.debug("Setting temperature to %s for zone %s", kwargs[ATTR_TEMPERATURE], self._zone_id)
            await self._write_data({"Target Temperature (°F)": kwargs[ATTR_TEMPERATURE]})

    async def async_set_hvac_mode(self, hvac_mode):
        mode = None
        if hvac_mode == HVAC_MODE_OFF:
            mode = "Off"
        elif hvac_mode == HVAC_MODE_HEAT:
            mode = "Heating"
        elif hvac_mode == HVAC_MODE_COOL:
            mode = "Cooling"
        
        if mode:
            self._zone_data['Mode'] = mode
            _LOGGER.debug("Setting HVAC mode to %s for zone %s", hvac_mode, self._zone_id)
            await self._write_data({"Mode": mode})

    async def async_set_fan_mode(self, fan_mode):
        self._zone_data['Fan Setting'] = fan_mode
        _LOGGER.debug("Setting fan mode to %s for zone %s", fan_mode, self._zone_id)
        await self._write_data({"Fan Setting": fan_mode})

    async def _write_data(self, data):
        """Write data to the MicroAir EasyTouch device via API."""
        try:
            url = f"http://{self._host}:5000/write"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"zone_id": self._zone_id, **data}) as response:
                    if response.status != 200:
                        _LOGGER.error("Error writing data to MicroAir EasyTouch device: %s", response.status)
        except Exception as e:
            _LOGGER.exception("Error writing data to MicroAir EasyTouch device")

    async def async_update(self):
        _LOGGER.debug("Updating data for zone %s", self._zone_id)
        try:
            url = f"http://{self._host}:5000/read"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        _LOGGER.error("Error fetching data from MicroAir EasyTouch device: %s", response.status)
                        return

                    output = await response.json()
                    _LOGGER.debug("API response: %s", output)

                    zones = {str(zone["Zone"]): zone for zone in output}
                    _LOGGER.debug("Parsed zones: %s", zones)

                    if str(self._zone_id) in zones:
                        self._zone_data = zones[str(self._zone_id)]
                    else:
                        _LOGGER.error("Zone ID %s not found in the API response", self._zone_id)
                        _LOGGER.debug("Available zones in response: %s", list(zones.keys()))
        except Exception as e:
            _LOGGER.exception("Error updating data from MicroAir EasyTouch device")
