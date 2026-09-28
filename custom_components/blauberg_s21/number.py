"""Configured manual percentages, independent of actual fan readings."""

import math

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pybls21 import BypassType

from .coordinator import S21ConfigEntry
from .entity import S21Entity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: S21ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entities = [S21Percentage(entry, "manual_fan_speed_percent")]
    if entry.runtime_data.data.bypass_type in (
        BypassType.BYPASS_ANALOGUE,
        BypassType.ROTOR_ANALOGUE,
    ):
        entities.append(S21Percentage(entry, "manual_bypass_position"))
    async_add_entities(entities)


class S21Percentage(S21Entity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, entry: S21ConfigEntry, key: str) -> None:
        super().__init__(entry, key)
        self._key = key
        self._attr_translation_key = key
        self._rotor = key == "manual_bypass_position" and (
            entry.runtime_data.data.bypass_type == BypassType.ROTOR_ANALOGUE
        )
        if self._rotor:
            self._attr_translation_key = "manual_rotor_speed"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        value = (
            data.manual_fan_speed_percent
            if self._key == "manual_fan_speed_percent"
            else data.manual_bypass_position
        )
        return 100 - value if self._rotor and value is not None else value

    async def async_set_native_value(self, value: float) -> None:
        if (
            isinstance(value, bool)
            or not math.isfinite(value)
            or not value.is_integer()
            or not 0 <= value <= 100
        ):
            raise ServiceValidationError("Percentage must be an integer from 0 to 100")
        percentage = int(value)

        async def command() -> None:
            client = self.coordinator.client
            if self._key == "manual_fan_speed_percent":
                # Configure the requested value before activating manual mode.
                await client.set_manual_fan_speed_percent(percentage)
                await client.set_fan_mode(255)
            else:
                # Setting a position does not implicitly change bypass/rotor mode.
                await client.set_bypass_position(
                    100 - percentage if self._rotor else percentage
                )

        await self.coordinator.async_execute(command)
