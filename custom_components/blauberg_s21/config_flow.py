"""Config flow for Blauberg S21 integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlow, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from .client import S21Client

from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_HOST): str, vol.Required(CONF_PORT, default=502): int}
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        host = data[CONF_HOST]
        port = data[CONF_PORT]
        client = S21Client(host, port)
        data = await client.poll()
    except Exception as exception:
        raise HomeAssistantError from exception

    title = (
        data.get('name')
        if data and getattr(data, "name", None)
        else f"Blauberg S21 ({host}:{port})"
    )
    unique_id = (
        str(data.get('unique_id'))
        if data and getattr(data, "unique_id", None)
        else f"{str(host).lower()}:{port}"
    )

    # Return info that will be used in the config entry.
    return {"title": title, "unique_id": unique_id}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Blauberg S21."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except HomeAssistantError:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(info["unique_id"])
            self._abort_if_unique_id_configured()
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
            )
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return S21OptionsFlow()

class S21OptionsFlow(OptionsFlow):
    """Handle Blauberg S21 options."""

    async def async_step_init(
            self,
            user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage the options."""

        if user_input is not None:
            # Store the new values
            return self.async_create_entry(
                title="",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=self.config_entry.data.get(CONF_HOST),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=self.config_entry.data.get(CONF_PORT, 502),
                ): int,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )