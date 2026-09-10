"""The Blauberg S21 integration."""
from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .client import S21Client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.NUMBER, Platform.BUTTON, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Blauberg S21 from a config entry."""

    async def _async_update_data():
        """Fetch the latest sensor data from the device."""
        client = hass.data[DOMAIN][config_entry.entry_id]["client"]
        data = await client.poll()
        return data

    async def _async_reset_maintenance_timer(call: ServiceCall) -> None:
        """Reset the maintenance timer."""
        client = hass.data[DOMAIN][config_entry.entry_id]["client"]
        await client.reset_filter_change_timer()

    async def _async_reset_alarm(call: ServiceCall) -> None:
        """Reset the maintenance timer."""
        client = hass.data[DOMAIN][config_entry.entry_id]["client"]
        await client.reset_alarm()

    host = config_entry.options.get(
        CONF_HOST,
        config_entry.data[CONF_HOST],
    )

    port = config_entry.options.get(
        CONF_PORT,
        config_entry.data.get(CONF_PORT, 502),
    )

    try:
        client = S21Client(host, port)
    except Exception as ex:
        raise ConfigEntryNotReady(
            f"Failed to connect to modbusTCP://{host}:{port}"
        ) from ex

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Blauberg S21 Sensor",
        config_entry=config_entry,
        update_method=_async_update_data,
        update_interval=timedelta(seconds=30)
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    #entry.async_on_unload(entry.add_update_listener(update_listener))

    # Reload the integration when options change
    config_entry.async_on_unload(
        config_entry.add_update_listener(async_reload_entry)
    )

    hass.services.async_register(
        DOMAIN,
        "reset_maintenance_timer",
        _async_reset_maintenance_timer,
    )
    hass.services.async_register(
        DOMAIN,
        "reset_alarm",
        _async_reset_alarm,
    )
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, "reset_maintenance_timer")
        hass.services.async_remove(DOMAIN, "reset_alarm")

    return unload_ok

# async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
#     """Handle options update."""
#     await hass.config_entries.async_reload(entry.entry_id)


# class S21SensorCoordinator(DataUpdateCoordinator):
#     """Shared data object for Blauberg S21 sensors."""
#
#     def __init__(
#         self,
#         hass: HomeAssistant,
#         config_entry: ConfigEntry,
#     ) -> None:
#         super().__init__(
#             hass,
#             _LOGGER,
#             name="Blauberg S21 Sensor",
#             config_entry=config_entry,
#             update_method=self._async_update_data,
#             update_interval=timedelta(seconds=30)
#         )
#         hass.data.setdefault(DOMAIN, {})
#
#         host = config_entry.data[CONF_HOST]
#         port = config_entry.data[CONF_PORT]
#
#         try:
#             self._client = S21Client(host, port)
#         except Exception as ex:
#             raise ConfigEntryNotReady(
#                 f"Failed to connect to modbusTCP://{host}:{port}"
#             ) from ex
#
#         hass.data[DOMAIN][config_entry.entry_id] = self._client
#

