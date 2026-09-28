"""Toggle the device's configured operating overrides."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pybls21 import ClimateDevice, S21Client

from .coordinator import S21ConfigEntry
from .entity import S21Entity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class S21SwitchDescription(SwitchEntityDescription):
    value_fn: Callable[[ClimateDevice], bool]
    on_fn: Callable[[S21Client], Awaitable[None]]
    off_fn: Callable[[S21Client], Awaitable[None]]


SWITCHES = (
    S21SwitchDescription(
        key="boost",
        translation_key="boost",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.is_boosting,
        on_fn=lambda c: c.boost_on(),
        off_fn=lambda c: c.boost_off(),
    ),
    S21SwitchDescription(
        key="timer",
        translation_key="timer",
        value_fn=lambda d: d.is_timer,
        on_fn=lambda c: c.set_timer_on(),
        off_fn=lambda c: c.set_timer_off(),
    ),
    S21SwitchDescription(
        key="schedule",
        translation_key="schedule",
        value_fn=lambda d: d.is_schedule_mode,
        on_fn=lambda c: c.set_scheduler_mode_on(),
        off_fn=lambda c: c.set_scheduler_mode_off(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: S21ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(S21Switch(entry, description) for description in SWITCHES)


class S21Switch(S21Entity, SwitchEntity):
    entity_description: S21SwitchDescription

    def __init__(
        self, entry: S21ConfigEntry, description: S21SwitchDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_execute(
            lambda: self.entity_description.on_fn(self.coordinator.client)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_execute(
            lambda: self.entity_description.off_fn(self.coordinator.client)
        )
