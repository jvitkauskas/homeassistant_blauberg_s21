"""The Blauberg S21 integration."""

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pybls21 import S21Client

from .const import DOMAIN
from .coordinator import S21ConfigEntry, S21Coordinator

PLATFORMS = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: S21ConfigEntry) -> bool:
    """Set up the client and fetch once before adding entities."""
    client = S21Client(entry.data[CONF_HOST], entry.data.get(CONF_PORT, 502))
    coordinator = S21Coordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: S21ConfigEntry) -> bool:
    """Unload entities and their coordinator subscriptions."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: S21ConfigEntry) -> bool:
    """Replace network-derived identifiers without replacing registered entities."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        registry = er.async_get(hass)
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entity.domain == Platform.CLIMATE and entity.platform == DOMAIN:
                registry.async_update_entity(
                    entity.entity_id, new_unique_id=f"{entry.entry_id}_climate"
                )
        devices = dr.async_get(hass)
        for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
            identifiers = {item for item in device.identifiers if item[0] != DOMAIN}
            identifiers.add((DOMAIN, entry.entry_id))
            devices.async_update_device(device.id, new_identifiers=identifiers)
        hass.config_entries.async_update_entry(
            entry, version=2, minor_version=1, unique_id=None
        )
    return True
