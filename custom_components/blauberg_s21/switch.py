"""Support for Blauberg S21 switches."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up Blauberg S21 switches from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    await coordinator.async_refresh()

    async_add_entities(
        [
            S21SwitchEntity(
                coordinator,
                client,
                config_entry,
                data_key="is_boosting",
                action_on_key="boost_on",
                action_off_key="boost_off",
                name="Boost to 100%",
                icon="mdi:rocket-launch",
                enabled=False,
            ),
        ],
        True,
    )

class S21SwitchEntity(SwitchEntity, S21Entity):
    """Representation of a Blauberg S21 button."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: S21Client,
        config_entry: ConfigEntry,
        data_key: str,
        action_on_key: str,
        action_off_key: str,
        name: str,
        icon: str,
        enabled: bool = True,
    ) -> None:
        super().__init__()
        self._data_key = data_key
        self._action_on_key = action_on_key
        self._action_off_key = action_off_key
        self._config_entry = config_entry

        self._attr_name = name
        self._attr_icon = icon

        self.coordinator = coordinator
        self.client = client

        entry_unique_id = config_entry.unique_id or getattr(self.coordinator.data, "unique_id", "unknown")
        self._attr_unique_id = f"{entry_unique_id}-{data_key}"

        self._attr_entity_registry_enabled_default = enabled

    @property
    def is_on(self) -> bool:
        """Return whether is on."""
        return self.coordinator.data.get(self._data_key, False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on."""
        func = getattr(self.client, self._action_on_key)
        await func()

        # Immediately update HA's local state
        self.coordinator.data[self._data_key] = True
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off."""
        func = getattr(self.client, self._action_off_key)
        await func()

        # Immediately update HA's local state
        self.coordinator.data[self._data_key] = False
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()

