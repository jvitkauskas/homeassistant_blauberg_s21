"""Readings from the coordinator's shared S21 snapshot."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pybls21 import BypassType, ClimateDevice

from .coordinator import S21ConfigEntry
from .entity import S21Entity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class S21SensorDescription(SensorEntityDescription):
    """A typed reading, with HA metadata kept outside the protocol library."""

    value_fn: Callable[[ClimateDevice], float | int | str | None]


def _filter_remaining(data: ClimateDevice) -> float | None:
    days, hours, minutes = (
        data.filter_countdown_days,
        data.filter_countdown_hours,
        data.filter_countdown_minutes,
    )
    if days is None or hours is None or minutes is None:
        return None
    return days * 24 + hours + minutes / 60


SENSORS = (
    S21SensorDescription(
        key="current_temperature",
        translation_key="supply_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.current_temperature,
    ),
    S21SensorDescription(
        key="current_intake_temperature",
        translation_key="intake_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.current_intake_temperature,
    ),
    S21SensorDescription(
        key="current_extract_temperature",
        translation_key="extract_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.current_extract_temperature,
    ),
    S21SensorDescription(
        key="current_exhaust_temperature",
        translation_key="exhaust_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.current_exhaust_temperature,
    ),
    S21SensorDescription(
        key="current_humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.current_humidity,
    ),
    S21SensorDescription(
        key="supply_pressure",
        translation_key="supply_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PA,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.supply_pressure,
    ),
    S21SensorDescription(
        key="extract_pressure",
        translation_key="extract_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PA,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.extract_pressure,
    ),
    S21SensorDescription(
        key="supply_airflow",
        translation_key="supply_airflow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.supply_airflow,
    ),
    S21SensorDescription(
        key="extract_airflow",
        translation_key="extract_airflow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.extract_airflow,
    ),
    S21SensorDescription(
        key="supply_fan_speed",
        translation_key="supply_fan_speed",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.supply_fan_speed,
    ),
    S21SensorDescription(
        key="extract_fan_speed",
        translation_key="extract_fan_speed",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.extract_fan_speed,
    ),
    S21SensorDescription(
        key="supply_fan_speed_percent",
        translation_key="supply_fan_speed_percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.supply_fan_speed_percent,
    ),
    S21SensorDescription(
        key="extract_fan_speed_percent",
        translation_key="extract_fan_speed_percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.extract_fan_speed_percent,
    ),
    S21SensorDescription(
        key="timer_countdown",
        translation_key="timer_countdown",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_registry_enabled_default=False,
        value_fn=lambda d: (
            d.timer_countdown.total_seconds() if d.timer_countdown is not None else None
        ),
    ),
    S21SensorDescription(
        key="operating_time_minutes",
        translation_key="operating_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.operating_time_minutes,
    ),
    S21SensorDescription(
        key="filter_remaining",
        translation_key="filter_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=_filter_remaining,
    ),
    S21SensorDescription(
        key="filter_state",
        translation_key="filter_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.filter_state,
    ),
    S21SensorDescription(
        key="alarm_state",
        translation_key="alarm_state",
        device_class=SensorDeviceClass.ENUM,
        options=["none", "alarm", "warning"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: {0: "none", 1: "alarm", 2: "warning"}.get(d.alarm_state),
    ),
    S21SensorDescription(
        key="bypass_position",
        translation_key="bypass_position",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.bypass_position,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: S21ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        S21Sensor(entry, description)
        for description in SENSORS
        if description.key != "bypass_position"
        or entry.runtime_data.data.bypass_type != BypassType.NOT_AVAILABLE
    )


class S21Sensor(S21Entity, SensorEntity):
    """A sensor whose properties never perform I/O."""

    entity_description: S21SensorDescription

    def __init__(
        self, entry: S21ConfigEntry, description: S21SensorDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description
        if (
            description.key == "bypass_position"
            and entry.runtime_data.data.bypass_type
            in (BypassType.ROTOR_DISCRETE, BypassType.ROTOR_ANALOGUE)
        ):
            # Optional IR51 semantics have not been verified as measured rotor speed.
            self._attr_translation_key = "rotor_position"

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key == "alarm_state":
            return {"alarm_codes": list(self.coordinator.data.alarm_codes)}
        return None
