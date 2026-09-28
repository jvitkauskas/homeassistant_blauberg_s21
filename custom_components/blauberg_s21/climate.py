"""Climate control backed by pybls21 device snapshots."""

import math
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pybls21 import HVACMode as S21HVACMode

from .coordinator import S21ConfigEntry
from .entity import S21Entity

PARALLEL_UPDATES = 0
FAN_LABELS = {1: FAN_LOW, 2: FAN_MEDIUM, 3: FAN_HIGH}
FAN_VALUES = {value: key for key, value in FAN_LABELS.items()} | {"custom": 255}


async def async_setup_entry(
    hass: HomeAssistant, entry: S21ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add the climate entity without a second startup poll."""
    async_add_entities([BlS21ClimateEntity(entry)])


class BlS21ClimateEntity(S21Entity, ClimateEntity):
    """The device's primary climate entity."""

    _attr_name = None
    _attr_translation_key = "s21climate"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = 0.1
    _attr_target_temperature_step = 1
    _attr_min_temp = 15
    _attr_max_temp = 30
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, entry: S21ConfigEntry) -> None:
        super().__init__(entry, "climate")

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data.current_temperature

    @property
    def target_temperature(self) -> float:
        return self.coordinator.data.target_temperature

    @property
    def current_humidity(self) -> float | None:
        return self.coordinator.data.current_humidity

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode(self.coordinator.data.hvac_mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        action = self.coordinator.data.hvac_action
        return HVACAction(action) if action is not None else None

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return [HVACMode(mode) for mode in self.coordinator.data.hvac_modes]

    def _fan_label(self, mode: int) -> str:
        if mode == 255:
            return "custom"
        if self.coordinator.data.max_fan_level == 3:
            return FAN_LABELS.get(mode, str(mode))
        return str(mode)

    @property
    def fan_mode(self) -> str | None:
        mode = self.coordinator.data.fan_mode
        return self._fan_label(mode) if mode is not None else None

    @property
    def fan_modes(self) -> list[str]:
        return [self._fan_label(mode) for mode in self.coordinator.data.fan_modes]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        try:
            mode = S21HVACMode(hvac_mode)
        except ValueError as error:
            raise ServiceValidationError("Unsupported HVAC mode") from error
        await self.coordinator.async_execute(
            lambda: self.coordinator.client.set_hvac_mode(mode)
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        try:
            mode = FAN_VALUES[fan_mode] if fan_mode in FAN_VALUES else int(fan_mode)
        except ValueError as error:
            raise ServiceValidationError("Invalid fan mode") from error
        if mode not in self.coordinator.data.fan_modes:
            raise ServiceValidationError("Fan mode is not supported by this device")
        await self.coordinator.async_execute(
            lambda: self.coordinator.client.set_fan_mode(mode)
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        value = kwargs.get(ATTR_TEMPERATURE)
        if value is None:
            return
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not float(value).is_integer()
        ):
            raise ServiceValidationError(
                "Temperature must be a whole number of degrees Celsius"
            )
        temperature = int(value)
        await self.coordinator.async_execute(
            lambda: self.coordinator.client.set_temperature(temperature)
        )

    async def async_turn_on(self) -> None:
        await self.coordinator.async_execute(self.coordinator.client.turn_on)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_execute(self.coordinator.client.turn_off)
