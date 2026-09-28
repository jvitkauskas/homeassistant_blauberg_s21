"""Shared identity and availability for device entities."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import S21ConfigEntry, S21Coordinator


class S21Entity(CoordinatorEntity[S21Coordinator]):
    """An entity backed by the config entry's single coordinator."""

    _attr_has_entity_name = True

    def __init__(self, entry: S21ConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        data = self.coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=data.name,
            manufacturer=data.manufacturer,
            model=data.model,
            sw_version=data.sw_version,
        )
