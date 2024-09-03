from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
)
from homeassistant.const import TEMP_FAHRENHEIT

from .api_client import MyClimateAPI
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the climate platform from a config entry."""
    api = hass.data[DOMAIN][entry.entry_id]
    status = await api.read_status()

    if status:
        zones = status["Zones"]
        entities = [MyClimateDevice(api, zone, entry.entry_id) for zone in zones]
        async_add_entities(entities, update_before_add=True)

class MyClimateDevice(ClimateEntity):
    """Representation of a single climate device."""

    def __init__(self, api, zone, entry_id):
        """Initialize the climate device."""
        self._api = api
        self._zone = zone
        self._entry_id = entry_id
        self._name = f"Climate Zone {zone['Zone']}"

        # Unique ID for each entity
        self._attr_unique_id = f"{entry_id}_zone_{zone['Zone']}"

        # Initialize attributes
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.FAN_ONLY, HVACMode.OFF]
        self._attr_hvac_mode = self._map_hvac_mode(zone["Mode"])  # Convert mode to HVACMode
        self._attr_temperature_unit = TEMP_FAHRENHEIT
        self._attr_target_temperature = zone["Heating Set Point (\u00b0F)"] if self._attr_hvac_mode == HVACMode.HEAT else zone["Cooling Set Point (\u00b0F)"]
        self._attr_current_temperature = zone["Inside Temperature (\u00b0F)"]  # Use inside temperature
        self._attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
        self._attr_fan_mode = self._map_fan_mode(zone["Fan Setting"])  # Convert fan setting
        self._attr_supported_features = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

    def _map_hvac_mode(self, mode):
        """Map the device-specific mode to Home Assistant's HVACMode."""
        mode_mapping = {
            "Heating": HVACMode.HEAT,
            "Cooling": HVACMode.COOL,
            "Fan Only": HVACMode.FAN_ONLY,
            "Off": HVACMode.OFF
        }
        return mode_mapping.get(mode, HVACMode.OFF)

    def _map_fan_mode(self, fan_setting):
        """Map the device-specific fan setting to Home Assistant fan mode."""
        fan_mapping = {
            "Low": FAN_LOW,
            "Medium": FAN_MEDIUM,
            "High": FAN_HIGH,
            "Auto": FAN_AUTO
        }
        return fan_mapping.get(fan_setting, FAN_AUTO)

    @property
    def unique_id(self):
        """Return the unique ID of the climate device."""
        return self._attr_unique_id

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def hvac_mode(self):
        """Return the current operation mode."""
        return self._attr_hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._attr_hvac_modes

    @property
    def fan_mode(self):
        """Return the current fan setting."""
        return self._attr_fan_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return self._attr_fan_modes

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return self._attr_temperature_unit

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._attr_target_temperature

    @property
    def current_temperature(self):
        """Return the current temperature inside the climate zone."""
        return self._attr_current_temperature

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._attr_supported_features

    async def async_set_temperature(self, **kwargs):
        """Set a new target temperature."""
        temperature = kwargs.get('temperature')
        if temperature is not None:
            changes = {"temperature": temperature}
            await self._api.send_command(self._zone["Zone"], changes)
            self._attr_target_temperature = temperature  # Update local state

    async def async_set_hvac_mode(self, hvac_mode):
        """Set a new HVAC mode."""
        changes = {"mode": hvac_mode}
        await self._api.send_command(self._zone["Zone"], changes)
        self._attr_hvac_mode = hvac_mode  # Update local state

    async def async_set_fan_mode(self, fan_mode):
        """Set a new fan mode."""
        changes = {"fan_speed": fan_mode}
        await self._api.send_command(self._zone["Zone"], changes)
        self._attr_fan_mode = fan_mode  # Update local state

    async def async_update(self):
        """Fetch new state data for the sensor."""
        status = await self._api.read_status()
        if status:
            zone = next((z for z in status["Zones"] if z["Zone"] == self._zone["Zone"]), None)
            if zone:
                self._attr_target_temperature = zone["Heating Set Point (\u00b0F)"] if self._attr_hvac_mode == HVACMode.HEAT else zone["Cooling Set Point (\u00b0F)"]
                self._attr_current_temperature = zone["Inside Temperature (\u00b0F)"]
                self._attr_hvac_mode = self._map_hvac_mode(zone["Mode"])  # Convert mode
                self._attr_fan_mode = self._map_fan_mode(zone["Fan Setting"])  # Convert fan setting
