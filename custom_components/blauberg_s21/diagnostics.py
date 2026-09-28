"""Share device readings without connection addresses or user configuration."""

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import S21ConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: S21ConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    snapshot = coordinator.data
    data = asdict(snapshot)
    data["legacy_inferred_hvac_action"] = data.pop("hvac_action")
    data.pop("timer_countdown")
    data["timer_countdown_seconds"] = (
        snapshot.timer_countdown.total_seconds()
        if snapshot.timer_countdown is not None
        else None
    )
    return {
        "last_update_success": coordinator.last_update_success,
        "cached_device": data,
    }
