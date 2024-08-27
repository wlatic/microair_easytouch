import logging
import aiohttp

from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    UnitOfTemperature,
    ClimateEntityFeature
)
from homeassistant.const import ATTR_TEMPERATURE

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MicroAir EasyTouch climate platform."""
    host = entry.data["host"]
    port = entry.data["port"]
    zones = entry.data["zones"]
    options = entry.options

    entities = []
    for zone_id, zone_data in zones.items():
        climate_entity = MicroAirEasyTouchClimate(
            hass,
            entry,
            f"microair_easytouch_zone_{zone_id}",
            zone_id,
            zone_data,
            host,
            port,
            options,
        )
        entities.append(climate_entity)

    async_add_entities(entities, True)
    _LOGGER.info("Added %d MicroAir EasyTouch climate entities", len(entities))

class MicroAirEasyTouchClimate(ClimateEntity):
    """Representation of a MicroAir EasyTouch climate entity."""

    def __init__(self, hass, entry, name, zone_id, initial_data, host, port, options):
        """Initialize the climate entity."""
        self.hass = hass
        self.entry = entry
        self._name = name
        self._zone_id = zone_id
        self._data = initial_data
        self._host = host
        self._port = port
        self._options = options

        self._current_temperature = float(initial_data["Inside Temperature (\u00b0F)"])
        self._target_temperature = float(initial_data["Target Temperature (\u00b0F)"])
        self._cooling_set_point = float(initial_data["Cooling Set Point (\u00b0F)"])
        self._heating_set_point = float(initial_data["Heating Set Point (\u00b0F)"])
        self._hvac_mode = self._get_hvac_mode(initial_data["Mode"])
        self._fan_mode = initial_data["Fan Setting"]
        self._heating_on = initial_data["Heating On"]
        self._cooling_on = initial_data["Cooling On"]
        self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
        self._attr_target_temperature_high = 86
        self._attr_target_temperature_low = 50
        self._attr_available = True
        self._enable_turn_on_off_backwards_compatibility = False

        hvac_modes = []
        if "heat" in self._options.get(f"zone_{zone_id}_hvac_modes", []):
            hvac_modes.append(HVACMode.HEAT)
        if "cool" in self._options.get(f"zone_{zone_id}_hvac_modes", []):
            hvac_modes.append(HVACMode.COOL)
        if "fan_only" in self._options.get(f"zone_{zone_id}_hvac_modes", []):
            hvac_modes.append(HVACMode.FAN_ONLY)
        hvac_modes.append(HVACMode.OFF)
        self._attr_hvac_modes = hvac_modes

        self._attr_fan_modes = ["Auto", "Low", "Medium", "High"]

    @property
    def name(self):
        """Return the name of the climate entity."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the climate entity."""
        return f"{self.entry.entry_id}_{self._zone_id}"

    @property
    def supported_features(self):
        """Return the list of supported features."""
        supported_features= ClimateEntityFeature.FAN_MODE

        if self.hvac_mode != HVACMode.FAN_ONLY:
            supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
        return supported_features

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return self._hvac_mode

    @property
    def hvac_action(self):
        """Return the current HVAC action (heating, cooling, or idle)."""
        if self._heating_on:
            return "heating"
        if self._cooling_on:
            return "cooling"
        return "idle"

    @property
    def fan_mode(self):
        """Return the current fan mode."""
        return self._fan_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return ["Auto", "Low", "Medium", "High"]

    async def async_update(self):
        """Update the entity data."""
        try:
            url = f"http://{self._host}:{self._port}/read"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=45) as response:
                    if response.status != 200:
                        _LOGGER.error("Error fetching data from MicroAir EasyTouch device: %s", response.status)
                        return

                    output = await response.json()
                    _LOGGER.debug("API response: %s", output)

                    zones = {str(zone["Zone"]): zone for zone in output}
                    _LOGGER.debug("Parsed zones: %s", zones)

                    if str(self._zone_id) in zones:
                        self._data = zones[str(self._zone_id)]
                        self._current_temperature = float(self._data["Inside Temperature (\u00b0F)"])
                        self._target_temperature = float(self._data["Target Temperature (\u00b0F)"])
                        self._cooling_set_point = float(self._data["Cooling Set Point (\u00b0F)"])
                        self._heating_set_point = float(self._data["Heating Set Point (\u00b0F)"])
                        self._hvac_mode = self._get_hvac_mode(self._data["Mode"])
                        self._fan_mode = self._data["Fan Setting"]
                        self._heating_on = self._data["Heating On"]
                        self._cooling_on = self._data["Cooling On"]
                        self.async_write_ha_state()
                    else:
                        _LOGGER.error("Zone ID %s not found in the API response", self._zone_id)
                        _LOGGER.debug("Available zones in response: %s", list(zones.keys()))
        except Exception as e:
            _LOGGER.exception("Error updating data from MicroAir EasyTouch device")

    def _get_hvac_mode(self, mode):
        if mode == "Off":
            return HVACMode.OFF
        elif mode == "Heating":
            return HVACMode.HEAT
        elif mode == "Cooling":
            return HVACMode.COOL
        elif mode == "Fan Only":
            return HVACMode.FAN_ONLY
        return HVACMode.OFF

    async def _send_command(self, payload):
        """Send command to the device."""
        url = f"http://{self._host}:{self._port}/write"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=45) as response:
                    if response.status != 200:
                        _LOGGER.error("Error sending command to MicroAir EasyTouch device: %s", response.status)
                        return False
                    _LOGGER.debug("Command response: %s", await response.json())
                    return True
        except Exception as e:
            _LOGGER.exception("Error sending command to MicroAir EasyTouch device")
            return False

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.warning(f"Mode {hvac_mode} is not supported for this zone")
            return

        payload = {
            "zone": self._zone_id,
            "power": "On" if hvac_mode != HVACMode.OFF else "Off"
        }
        if hvac_mode == HVACMode.HEAT:
            payload["mode"] = 1
        elif hvac_mode == HVACMode.COOL:
            payload["mode"] = 4
        elif hvac_mode == HVACMode.FAN_ONLY:
            payload["mode"] = 3

        success = await self._send_command(payload)
        if success:
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        if HVACMode.FAN_ONLY in self._attr_hvac_modes and self._hvac_mode == HVACMode.FAN_ONLY:
            _LOGGER.warning("Cannot set temperature in fan-only mode")
            return

        # Determine if heating or cooling based on current hvac mode
        payload = {
            "zone": self._zone_id,
            "temperature": int(temperature)
        }
        if self._hvac_mode == HVACMode.HEAT:
            payload["mode"] = 1  # Ensure mode is set to heating
        elif self._hvac_mode == HVACMode.COOL:
            payload["mode"] = 4  # Ensure mode is set to cooling

        success = await self._send_command(payload)
        if success:
            self._target_temperature = temperature
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        fan_modes = {"Auto": 3, "Low": 0, "Medium": 1, "High": 2}
        if fan_mode not in fan_modes:
            _LOGGER.error("Invalid fan mode: %s", fan_mode)
            return

        payload = {
            "zone": self._zone_id,
            "fan": fan_modes[fan_mode]
        }
        success = await self._send_command(payload)
        if success:
            self._fan_mode = fan_mode
            self.async_write_ha_state()
