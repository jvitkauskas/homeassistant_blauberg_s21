"""Support for Blauberg S21 buttons."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up Blauberg S21 buttons from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    await coordinator.async_refresh()

    async_add_entities(
        [
            S21ButtonEntity(
                coordinator,
                client,
                config_entry,
                data_key="reset_filter_change_timer",
                name="Reset Filter Maintenance Timer",
                icon="mdi:refresh",
            ),
            S21ButtonEntity(
                coordinator,
                client,
                config_entry,
                data_key="reset_alarm",
                name="Reset Alarm",
                icon="mdi:alarm-off",
            ),
        ],
        True,
    )

class S21ButtonEntity(ButtonEntity, S21Entity):
    """Representation of a Blauberg S21 button."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: S21Client,
        config_entry: ConfigEntry,
        data_key: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__()
        self._data_key = data_key
        self._config_entry = config_entry

        self._attr_name = name
        self._attr_icon = icon

        self.coordinator = coordinator
        self.client = client

        entry_unique_id = config_entry.unique_id or getattr(self.coordinator.data, "unique_id", "unknown")
        self._attr_unique_id = f"{entry_unique_id}-{data_key}"


    async def async_press(self) -> None:
        """Handle the button press."""
        func = getattr(self.client, self._data_key)
        await func()
