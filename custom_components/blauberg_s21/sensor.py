"""Support for Blauberg S21 sensors."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfPressure, UnitOfTime, UnitOfRatio, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .models import S21Entity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Blauberg S21 sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    await coordinator.async_refresh()

    async_add_entities(
        [
            BlS21TemperatureSensor(
                coordinator,
                config_entry,
                data_key="current_supply_temperature",
                name="Supply Temperature (to inside)",
                icon="mdi:home-thermometer",
            ),
            BlS21TemperatureSensor(
                coordinator,
                config_entry,
                data_key="current_intake_temperature",
                name="Intake Temperature (from outside)",
                icon="mdi:thermometer",
            ),
            BlS21TemperatureSensor(
                coordinator,
                config_entry,
                data_key="current_extract_temperature",
                name="Extract Temperature (from rooms)",
                icon="mdi:home-thermometer-outline",
            ),
            BlS21TemperatureSensor(
                coordinator,
                config_entry,
                data_key="current_exhaust_temperature",
                name="Exhaust Temperature (to outside)",
                icon="mdi:thermometer",
            ),
            BlS21HumiditySensor(
                coordinator,
                config_entry,
                data_key="current_humidity",
                name="Humidity",
                icon="mdi:water-percent",
                enabled=False,
            ),
            BlS21AirflowSensor(
                coordinator,
                config_entry,
                data_key="supply_airflow",
                name="Supply Airflow (to inside)",
                icon="mdi:gauge",
                enabled=False,
            ),
            BlS21AirflowSensor(
                coordinator,
                config_entry,
                data_key="extract_airflow",
                name="Exhaust Airflow (from inside)",
                icon="mdi:gauge",
                enabled=False,
            ),
            BlS21PressureSensor(
                coordinator,
                config_entry,
                data_key="supply_pressure",
                name="Supply Pressure (to inside)",
                icon="mdi:gauge",
                enabled=False,
            ),
            BlS21PressureSensor(
                coordinator,
                config_entry,
                data_key="extract_pressure",
                name="Exhaust Pressure (from inside)",
                icon="mdi:gauge",
                enabled=False,
            ),
            BlS21PercentSensor(
                coordinator,
                config_entry,
                data_key="supply_fan_state",
                name="Supply Fan (to inside)",
                icon="mdi:gauge",
            ),
            BlS21PercentSensor(
                coordinator,
                config_entry,
                data_key="extract_fan_state",
                name="Extract Fan (from inside)",
                icon="mdi:gauge",
            ),
            BlS21RPMSensor(
                coordinator,
                config_entry,
                data_key="supply_fan_speed",
                name="Supply Fan Speed (to inside)",
                icon="mdi:gauge",
            ),
            BlS21RPMSensor(
                coordinator,
                config_entry,
                data_key="extract_fan_speed",
                name="Extract Fan Speed (from inside)",
                icon="mdi:gauge",
            ),
            BlS21DurationSensor(
                coordinator,
                config_entry,
                UnitOfTime.MINUTES,
                data_key="engine_running_time",
                name="Engine Total Working Time",
                icon="mdi:engine",
            ),
            BlS21DurationSensor(
                coordinator,
                config_entry,
                UnitOfTime.DAYS,
                data_key="filter_countdown_days",
                name="Filter Maintenance",
                icon="mdi:filter-cog",
            ),
            BlS21TextSensor(
                coordinator,
                config_entry,
                data_key="filter_state",
                name="Filter",
                icon="mdi:filter",
            ),
            BlS21PercentSensor(
                coordinator,
                config_entry,
                data_key="bypass_state",
                name="Bypass Open State",
                icon="mdi:transit-skip",
            ),
            BlS21AlarmSensor(
                coordinator,
                config_entry,
                data_key="alarm_state",
                name="Alarm",
            ),
        ],
        True,
    )

class BlS21TemperatureSensor(SensorEntity, S21Entity):
    """Representation of a Blauberg S21 temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        data_key: str,
        name: str,
        icon: str,
        enabled: bool = True,
    ) -> None:
        super().__init__()
        self._data_key = data_key
        self._config_entry = config_entry

        self._attr_name = name
        self._attr_icon = icon

        self.coordinator = coordinator

        entry_unique_id = config_entry.unique_id or getattr(self.coordinator.data, "unique_id", "unknown")
        self._attr_unique_id = f"{entry_unique_id}-{data_key}"

        self._attr_entity_registry_enabled_default = enabled

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key, None)

class BlS21AirflowSensor(BlS21TemperatureSensor):
    """Representation of a Blauberg S21 pressure sensor."""

    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_native_unit_of_measurement = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT


class BlS21PressureSensor(BlS21TemperatureSensor):
    """Representation of a Blauberg S21 pressure sensor."""

    _attr_device_class = SensorDeviceClass.PRESSURE
    _attr_native_unit_of_measurement = UnitOfPressure.PA
    _attr_state_class = SensorStateClass.MEASUREMENT


class BlS21HumiditySensor(BlS21TemperatureSensor):
    """Representation of a Blauberg S21 humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = UnitOfRatio.PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT


class BlS21RPMSensor(BlS21TemperatureSensor):
    """Representation of a Blauberg S21 rpm sensor."""

    _attr_device_class = None
    _attr_native_unit_of_measurement = "RPM"
    _attr_state_class = SensorStateClass.MEASUREMENT

class BlS21DurationSensor(BlS21TemperatureSensor):
    """Representation of a Blauberg S21 duration sensor."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        unit_of_measurement: UnitOfTime,
        data_key: str,
        name: str,
        icon: str,
        enabled: bool = True,
    ) -> None:
        self._attr_native_unit_of_measurement = unit_of_measurement
        super().__init__(coordinator, config_entry, data_key, name, icon, enabled)

class BlS21PercentSensor(BlS21TemperatureSensor):
    """Representation of a Blauberg S21 percent sensor."""

    _attr_device_class = None
    _attr_native_unit_of_measurement = UnitOfRatio.PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT


class BlS21AlarmSensor(BlS21TemperatureSensor):
    """Representation of a Blauberg S21 alarm sensor."""

    _attr_device_class = None
    _attr_native_unit_of_measurement = None
    _attr_state_class = None

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        data_key: str,
        name: str,
        enabled: bool = True,
    ) -> None:
        icon = "mdi:alarm-light-off"
        super().__init__(coordinator, config_entry, data_key, name, icon, enabled)

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        state = self.coordinator.data.get(self._data_key, "Unknown")

        if state == "No":
            self._attr_icon = "mdi:alarm-light-off"
        else:
            self._attr_icon = "mdi:alarm-light"

        return state

class BlS21TextSensor(BlS21TemperatureSensor):
    """Representation of a Blauberg S21 text sensor."""

    _attr_device_class = None
    _attr_native_unit_of_measurement = None
    _attr_state_class = None
