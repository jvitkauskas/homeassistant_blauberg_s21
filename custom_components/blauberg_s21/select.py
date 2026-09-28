"""Select the bypass/rotor control mode when fitted."""

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pybls21 import BypassMode, BypassType

from .coordinator import S21ConfigEntry
from .entity import S21Entity

PARALLEL_UPDATES = 0
MODES = {"closed": BypassMode.CLOSED, "open": BypassMode.OPEN, "auto": BypassMode.AUTO}


async def async_setup_entry(
    hass: HomeAssistant, entry: S21ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if entry.runtime_data.data.bypass_type != BypassType.NOT_AVAILABLE:
        async_add_entities([S21BypassMode(entry)])


class S21BypassMode(S21Entity, SelectEntity):
    _attr_translation_key = "bypass_mode"
    _attr_options = list(MODES)

    def __init__(self, entry: S21ConfigEntry) -> None:
        super().__init__(entry, "bypass_mode")
        self._attr_translation_key = {
            BypassType.ROTOR_DISCRETE: "rotor_mode",
            BypassType.ROTOR_ANALOGUE: "rotor_analogue_mode",
            BypassType.BYPASS_ANALOGUE: "bypass_analogue_mode",
        }.get(entry.runtime_data.data.bypass_type, "bypass_mode")

    @property
    def current_option(self) -> str | None:
        mode = self.coordinator.data.bypass_mode
        return next((option for option, value in MODES.items() if value == mode), None)

    async def async_select_option(self, option: str) -> None:
        if option not in MODES:
            raise ServiceValidationError("Unsupported bypass mode")
        await self.coordinator.async_execute(
            lambda: self.coordinator.client.set_bypass_mode(MODES[option])
        )
