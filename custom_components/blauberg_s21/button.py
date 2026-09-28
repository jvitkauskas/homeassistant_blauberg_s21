"""Device maintenance actions."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import S21ConfigEntry
from .entity import S21Entity

PARALLEL_UPDATES = 0
BUTTONS = (
    ButtonEntityDescription(
        key="reset_filter_change_timer",
        translation_key="reset_filter",
        entity_category=EntityCategory.CONFIG,
    ),
    ButtonEntityDescription(
        key="reset_alarm",
        translation_key="reset_alarm",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: S21ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(S21Button(entry, description) for description in BUTTONS)


class S21Button(S21Entity, ButtonEntity):
    def __init__(
        self, entry: S21ConfigEntry, description: ButtonEntityDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        client = self.coordinator.client
        command = (
            client.reset_alarm
            if self.entity_description.key == "reset_alarm"
            else client.reset_filter_change_timer
        )
        await self.coordinator.async_execute(command)
