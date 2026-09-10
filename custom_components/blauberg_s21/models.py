"""Models for the Blauberg S21 integration."""

from homeassistant.components.climate import FAN_LOW, FAN_MEDIUM, FAN_HIGH
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .device import build_device_info

ALARM_STATES: dict[int] = {
    0: "No",
    1: "Alarm",
    2: "Warning"
}

FILTER_STATES: dict[int] = {
    0: "Clean",
    1: "The intake supply filter is clogged,",
    2: "The extract filter is clogged,",
    3: "Both filters are clogged or the filter replacement timer has gone off"
}

S21_TO_HA_FAN_MODE = {
    1: FAN_LOW,
    2: FAN_MEDIUM,
    3: FAN_HIGH,
    255: "custom"
}

class S21Entity(Entity):
    _attr_should_poll = False

    """Representation of a S21 entity."""
    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        if self.coordinator.data is None:
            return False

        return self.coordinator.data.get("available", False)

    @property
    def device_info(self) -> DeviceInfo | None:
        entry_unique_id = (
            self._config_entry.unique_id
            or self.coordinator.data.get("unique_id", "unknown")
        )
        return build_device_info(self.coordinator, entry_unique_id, self._config_entry.title)

