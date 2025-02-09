"""Support for climate device."""
from typing import Any, Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pybls21.client import S21Client
from pybls21.models import HVACAction as BlS21HVACAction
from pybls21.models import HVACMode as BlS21HVACMode

from .const import DOMAIN

HA_TO_S21_HVACMODE = {
    HVACMode.OFF: BlS21HVACMode.OFF,
    HVACMode.HEAT: BlS21HVACMode.HEAT,
    HVACMode.COOL: BlS21HVACMode.COOL,
    HVACMode.AUTO: BlS21HVACMode.AUTO,
    HVACMode.FAN_ONLY: BlS21HVACMode.FAN_ONLY,
}

S21_TO_HA_HVACMODE = {v: k for k, v in HA_TO_S21_HVACMODE.items()}

S21_TO_HA_HVACACTION = {
    BlS21HVACAction.COOLING: HVACAction.COOLING,
    BlS21HVACAction.FAN: HVACAction.FAN,
    BlS21HVACAction.HEATING: HVACAction.HEATING,
    BlS21HVACAction.IDLE: HVACAction.IDLE,
    BlS21HVACAction.OFF: HVACAction.OFF,
}

S21_TO_HA_FAN_MODE = {1: FAN_LOW, 2: FAN_MEDIUM, 3: FAN_HIGH, 255: "custom"}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Blauberg S21 climate entity."""
    client: S21Client = hass.data[DOMAIN][config_entry.entry_id]

    entities = [BlS21ClimateEntity(client)]
    async_add_entities(entities, True)


class BlS21ClimateEntity(ClimateEntity):
    """Representation of a Blauberg S21 climate feature."""

    _attr_translation_key = "s21climate"

    def __init__(self, client: S21Client) -> None:
        self._client = client

    @property
    def available(self) -> bool:
        if self._client.device:
            return self._client.device.available
        return False

    @property
    def name(self) -> Optional[str]:
        if self._client.device:
            return self._client.device.name

    @property
    def unique_id(self) -> Optional[str]:
        if self._client.device:
            return self._client.device.unique_id

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS

    @property
    def precision(self) -> Optional[float]:
        if self._client.device:
            return self._client.device.precision

    @property
    def current_temperature(self) -> Optional[float]:
        if self._client.device:
            return self._client.device.current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        if self._client.device:
            return self._client.device.target_temperature

    @property
    def target_temperature_step(self) -> Optional[float]:
        if self._client.device:
            return self._client.device.target_temperature_step

    @property
    def max_temp(self) -> Optional[float]:
        if self._client.device:
            return self._client.device.max_temp

    @property
    def min_temp(self) -> Optional[float]:
        if self._client.device:
            return self._client.device.min_temp

    @property
    def current_humidity(self) -> Optional[float]:
        if self._client.device:
            return self._client.device.current_humidity

    @property
    def hvac_mode(self) -> Optional[HVACMode]:
        if self._client.device:
            return S21_TO_HA_HVACMODE[self._client.device.hvac_mode]

    @property
    def hvac_action(self) -> Optional[str]:
        if self._client.device:
            return S21_TO_HA_HVACACTION[self._client.device.hvac_action]

    @property
    def hvac_modes(self) -> Optional[list[HVACMode]]:
        if self._client.device:
            return [S21_TO_HA_HVACMODE[m] for m in self._client.device.hvac_modes]

    @property
    def fan_mode(self) -> Optional[str]:
        if self._client.device:
            if self._client.device.max_fan_level == 3:
                return S21_TO_HA_FAN_MODE[self._client.device.fan_mode]
            return str(self._client.device.fan_mode)

    @property
    def fan_modes(self) -> Optional[list[str]]:
        if self._client.device:
            if self._client.device.max_fan_level == 3:
                return [S21_TO_HA_FAN_MODE[m] for m in self._client.device.fan_modes]
            return [str(m) for m in self._client.device.fan_modes]

    @property
    def supported_features(self) -> ClimateEntityFeature:
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def manufacturer(self) -> Optional[str]:
        """Return the manufacturer of the device."""
        if self._client.device:
            return self._client.device.manufacturer

    @property
    def model(self) -> Optional[str]:
        """Return the model of the device."""
        if self._client.device:
            return self._client.device.model

    @property
    def sw_version(self) -> Optional[str]:
        """Return the software version of the device."""
        if self._client.device:
            return self._client.device.sw_version

    @property
    def icon(self) -> Optional[str]:
        if self._client.device:
            if not self._client.device.available:
                return "mdi:lan-disconnect"
            if self._client.device.is_boosting:
                return "mdi:fan-plus"
            if self._client.device.hvac_action == BlS21HVACAction.OFF:
                return "mdi:fan-off"
            if self._client.device.hvac_action == BlS21HVACAction.IDLE:
                return "mdi:fan-remove"
            if self._client.device.max_fan_level == 3:
                if self._client.device.fan_mode == 1:
                    return "mdi:fan-speed-1"
                if self._client.device.fan_mode == 2:
                    return "mdi:fan-speed-2"
                if self._client.device.fan_mode == 3:
                    return "mdi:fan-speed-3"
            if self._client.device.hvac_action == BlS21HVACAction.COOLING:
                return "mdi:fan-chevron-down"
            if self._client.device.hvac_action == BlS21HVACAction.HEATING:
                return "mdi:fan-chevron-up"
            if self._client.device.hvac_action == BlS21HVACAction.FAN:
                return "mdi:fan"
        return "mdi:fan"

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._client.set_hvac_mode(HA_TO_S21_HVACMODE[hvac_mode])

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        int_fan_mode = (
            255
            if fan_mode == "custom"
            else 1
            if fan_mode == FAN_LOW
            else 2
            if fan_mode == FAN_MEDIUM
            else 3
            if fan_mode == FAN_HIGH
            else int(fan_mode)
        )
        await self._client.set_fan_mode(int_fan_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self._client.set_temperature(int(temperature))

    async def async_update(self) -> None:
        await self._client.poll()
