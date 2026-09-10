"""Support for Blauberg S21 sensors."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import S21Client
from .const import DOMAIN
from .models import S21Entity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Blauberg S21 sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    await coordinator.async_refresh()

    async_add_entities(
        [
            S21NumberFanPercentEntity(
                coordinator,
                client,
                config_entry,
                data_key="supply_fan_state",
                action_key="set_manual_fan_speed_percent",
                name="Manual Set Fan Speed Percent",
                icon="mdi:fan",
            ),
        ],
        True,
    )

class S21NumberFanPercentEntity(NumberEntity, S21Entity):
    """Representation of a Blauberg S21 button."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: S21Client,
        config_entry: ConfigEntry,
        data_key: str,
        action_key: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__()
        self._data_key = data_key
        self._action_key = action_key
        self._config_entry = config_entry

        self._attr_name = name
        self._attr_icon = icon

        self.coordinator = coordinator
        self.client = client

        entry_unique_id = config_entry.unique_id or getattr(self.coordinator.data, "unique_id", "unknown")
        self._attr_unique_id = f"{entry_unique_id}-{data_key}"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key, None)

#    async def async_set_value(self, value: float) -> None:
    async def async_set_native_value(self, value: float) -> None:
        # Set fan mode to 255 (custom, otherwise it is not allowed to set percent!)
        func = getattr(self.client, "set_fan_mode")
        await func(255)

        """Set new value."""
        func = getattr(self.client, self._action_key)
        await func(int(value))

        # Immediately update HA's local state
        self.coordinator.data["fan_mode"] = 255
        self.coordinator.data[self._data_key] = int(value)
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()
