"""Configure and reconfigure a Blauberg S21 endpoint."""

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import config_validation as cv
from pybls21 import DiscoveredDevice, S21Client, S21Error, UnsupportedDeviceException

from .const import DOMAIN
from .coordinator import OPERATION_TIMEOUT
from .discovery import async_discover_devices, async_identify_device

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): cv.string,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, 502)): cv.port,
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Use controller IDs for duplicate detection, keeping entity identity stable."""

    def __init__(self) -> None:
        self._devices: dict[str, DiscoveredDevice] = {}
        self._selected: DiscoveredDevice | None = None

    VERSION = 2
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_manual(user_input)
        self._devices = {
            device.device_id: device
            for device in await async_discover_devices(self.hass)
        }
        if not self._devices:
            return await self.async_step_manual()
        return self.async_show_menu(
            step_id="user", menu_options=["discovered", "manual"]
        )

    async def async_step_discovered(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._selected = self._devices[user_input["device"]]
            return await self.async_step_manual()
        return self.async_show_form(
            step_id="discovered",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): vol.In(
                        {
                            key: f"{device.host} ({key})"
                            for key, device in self._devices.items()
                        }
                    )
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_configure("manual", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_configure("reconfigure", user_input)

    async def _async_configure(
        self, step: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry() if step == "reconfigure" else None
        defaults = (
            dict(entry.data)
            if entry
            else (
                {CONF_HOST: self._selected.host, CONF_PORT: 502}
                if self._selected
                else {}
            )
        )
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_HOST: user_input[CONF_HOST].strip().lower(),
                CONF_PORT: user_input[CONF_PORT],
            }
            defaults = data
            if not data[CONF_HOST]:
                errors[CONF_HOST] = "invalid_host"
            elif any(
                other.entry_id != (entry.entry_id if entry else None)
                and str(other.data[CONF_HOST]).strip().lower() == data[CONF_HOST]
                and other.data.get(CONF_PORT, 502) == data[CONF_PORT]
                for other in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")
            else:
                try:
                    async with asyncio.timeout(OPERATION_TIMEOUT):
                        device = await S21Client(
                            data[CONF_HOST], data[CONF_PORT]
                        ).poll()
                except UnsupportedDeviceException:
                    errors["base"] = "unsupported_device"
                except S21Error, TimeoutError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error validating S21 endpoint")
                    errors["base"] = "unknown"
                else:
                    identity = await async_identify_device(data[CONF_HOST])
                    expected = (
                        entry.unique_id
                        if entry
                        else (self._selected.device_id if self._selected else None)
                    )
                    if expected and identity != expected:
                        errors["base"] = (
                            "wrong_device" if identity else "cannot_identify"
                        )
                    elif identity and any(
                        other.entry_id != (entry.entry_id if entry else None)
                        and other.unique_id == identity
                        for other in self._async_current_entries()
                    ):
                        return self.async_abort(reason="already_configured")
                    elif entry:
                        if identity:
                            self.hass.config_entries.async_update_entry(
                                entry, unique_id=identity
                            )
                        return self.async_update_reload_and_abort(
                            entry, data_updates=data
                        )
                    else:
                        if identity:
                            await self.async_set_unique_id(identity)
                            self._abort_if_unique_id_configured()
                        return self.async_create_entry(title=device.name, data=data)
        return self.async_show_form(
            step_id=step, data_schema=_schema(defaults), errors=errors
        )
