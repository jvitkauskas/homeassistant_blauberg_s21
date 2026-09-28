"""One serialized update stream for all entities on a device."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryError,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pybls21 import ClimateDevice, S21Client, S21Error, UnsupportedDeviceException

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
OPERATION_TIMEOUT = 20


class S21Coordinator(DataUpdateCoordinator[ClimateDevice]):
    """Poll once for every entity, with bounded I/O and confirmed write results."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: S21Client
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=30),
            always_update=False,
        )
        self.client = client
        self._operation_lock = asyncio.Lock()

    async def _async_update_data(self) -> ClimateDevice:
        try:
            async with asyncio.timeout(OPERATION_TIMEOUT), self._operation_lock:
                return await self.client.poll()
        except UnsupportedDeviceException as error:
            raise ConfigEntryError("Endpoint is not a supported S21 device") from error
        except (S21Error, TimeoutError) as error:
            raise UpdateFailed(f"Unable to read S21: {error}") from error

    async def async_execute(self, command: Callable[[], Awaitable[None]]) -> None:
        """Serialize a complete command and its confirming poll with updates."""
        try:
            async with asyncio.timeout(OPERATION_TIMEOUT), self._operation_lock:
                await command()
                data = await self.client.poll()
        except ValueError as error:
            raise ServiceValidationError(str(error)) from error
        except (S21Error, TimeoutError) as error:
            self.async_set_update_error(UpdateFailed(str(error)))
            raise HomeAssistantError(
                "Unable to communicate with the S21 device"
            ) from error
        self.async_set_updated_data(data)


type S21ConfigEntry = ConfigEntry[S21Coordinator]
