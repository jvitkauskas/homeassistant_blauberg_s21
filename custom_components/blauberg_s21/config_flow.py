"""Configure and reconfigure a Blauberg S21 endpoint."""

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import config_validation as cv
from pybls21 import S21Client, S21Error, UnsupportedDeviceException

from .const import DOMAIN
from .coordinator import OPERATION_TIMEOUT

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): cv.string,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, 502)): cv.port,
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """No hardware ID is available; entity identity belongs to the config entry."""

    VERSION = 2
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_configure("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_configure("reconfigure", user_input)

    async def _async_configure(
        self, step: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry() if step == "reconfigure" else None
        defaults = dict(entry.data) if entry else {}
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
                    if entry:
                        return self.async_update_reload_and_abort(
                            entry, data_updates=data
                        )
                    return self.async_create_entry(title=device.name, data=data)
        return self.async_show_form(
            step_id=step, data_schema=_schema(defaults), errors=errors
        )
