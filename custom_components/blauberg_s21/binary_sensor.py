"""Human-readable maintenance indicators from documented device status values."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pybls21 import ClimateDevice

from .coordinator import S21ConfigEntry
from .entity import S21Entity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class S21BinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[ClimateDevice], bool | None]


SENSORS = (
    S21BinarySensorDescription(
        key="boost_active",
        translation_key="boost_active",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.is_boosting,
    ),
    S21BinarySensorDescription(
        key="filter_attention",
        translation_key="filter_attention",
        device_class=BinarySensorDeviceClass.PROBLEM,
        # IR31: 1 intake filter, 2 extract filter, 3 both or expired timer.
        value_fn=lambda d: {0: False, 1: True, 2: True, 3: True}.get(d.filter_state),
    ),
    S21BinarySensorDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        # IR38: 1 alarm, 2 warning. Unrecognized values must remain unknown.
        value_fn=lambda d: {0: False, 1: True, 2: True}.get(d.alarm_state),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: S21ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(S21BinarySensor(entry, description) for description in SENSORS)


class S21BinarySensor(S21Entity, BinarySensorEntity):
    entity_description: S21BinarySensorDescription

    def __init__(
        self, entry: S21ConfigEntry, description: S21BinarySensorDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
