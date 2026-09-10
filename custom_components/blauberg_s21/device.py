"""Device helper."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

def build_device_info(
        coordinator: DataUpdateCoordinator,
        unique_id: str,
        name: str = "Blauberg S21",
        manufacturer: str = "Blauberg",
        model: str | None = None,
        sw_version: str | None = None,
) -> DeviceInfo | None:
        """Return information used by Home Assistant to register the device."""
        if not unique_id:
            return None

        if coordinator.data:
            name = coordinator.data.get('name', name)
            manufacturer = coordinator.data.get('manufacturer', manufacturer)
            model = coordinator.data.get('model')
            sw_version = coordinator.data.get('sw_version')

        return DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=name,
            manufacturer=manufacturer,
            model=model,
            sw_version=sw_version,
        )