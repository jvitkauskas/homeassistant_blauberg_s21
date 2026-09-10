"""Support for climate device."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import S21Client
from .const import DOMAIN
from .models import S21Entity, S21_TO_HA_FAN_MODE

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Blauberg S21 climate entity."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    await coordinator.async_refresh()

    entities = [BlS21ClimateEntity(coordinator, client, config_entry)]
    async_add_entities(entities, True)


class BlS21ClimateEntity(ClimateEntity, S21Entity):
    """Representation of a Blauberg S21 climate feature."""

    _attr_translation_key = "s21climate"

    def __init__(self, coordinator: DataUpdateCoordinator, client: S21Client, config_entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self.client = client
        self._config_entry = config_entry

    @property
    def name(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get('name')

    @property
    def unique_id(self) -> str | None:
        if self._config_entry.unique_id:
            return self._config_entry.unique_id
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get('unique_id')

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS

    @property
    def precision(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('precision')

    @property
    def current_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('current_supply_temperature')

    @property
    def target_temperature(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('target_temperature')

    @property
    def target_temperature_step(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('target_temperature_step')

    @property
    def max_temp(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('max_temp')

    @property
    def min_temp(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('min_temp')

    @property
    def current_humidity(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('current_humidity')

    @property
    def hvac_mode(self) -> HVACMode | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('hvac_mode')

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get('hvac_action')

    @property
    def hvac_modes(self) -> list[HVACMode] | None:
        return [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.FAN_ONLY]

    @property
    def fan_mode(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return S21_TO_HA_FAN_MODE.get(self.coordinator.data.get('fan_mode'))

    @property
    def fan_modes(self) -> list[str] | None:
        if self.coordinator.data is None:
            return None
        return [item for key, item in S21_TO_HA_FAN_MODE.items()]

    @property
    def supported_features(self) -> ClimateEntityFeature:
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def icon(self) -> str | None:
        if self.coordinator.data is None:
            return "mdi:fan"
        if not self.coordinator.data.get('available'):
            return "mdi:lan-disconnect"
        if self.coordinator.data.get('is_boosting'):
            return "mdi:fan-plus"
        if self.coordinator.data.get('hvac_action') == HVACAction.OFF:
            return "mdi:fan-off"
        if self.coordinator.data.get('hvac_action') == HVACAction.IDLE:
            return "mdi:fan-remove"
        if self.coordinator.data.get('max_fan_level') == 3:
            if self.coordinator.data.get('fan_mode') == 1:
                return "mdi:fan-speed-1"
            if self.coordinator.data.get('fan_mode') == 2:
                return "mdi:fan-speed-2"
            if self.coordinator.data.get('fan_mode') == 3:
                return "mdi:fan-speed-3"
            else:
                return "mdi:fan"
        if self.coordinator.data.get('hvac_action') == HVACAction.COOLING:
            return "mdi:fan-chevron-down"
        if self.coordinator.data.get('hvac_action') == HVACAction.HEATING:
            return "mdi:fan-chevron-up"
        if self.coordinator.data.get('hvac_action') == HVACAction.FAN:
            return "mdi:fan"
        else:
            return "mdi:fan"

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.client.set_hvac_mode(hvac_mode)

        self.coordinator.data["hvac_mode"] = hvac_mode
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        previous_fan_mode = self.fan_mode
        int_fan_mode = (
            255
            if fan_mode == "custom"
            else 1
            if fan_mode == FAN_LOW
            else 2
            if fan_mode == FAN_MEDIUM
            else 3
            if fan_mode == FAN_HIGH
            else int(fan_mode)
        )
        await self.client.set_fan_mode(int_fan_mode)

        self.coordinator.data["fan_mode"] = int_fan_mode
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

        current_fan_mode = self.fan_mode
        if (
            self.hass
            and self.entity_id
            and previous_fan_mode is not None
            and current_fan_mode is not None
            and previous_fan_mode != current_fan_mode
        ):
            self.hass.bus.async_fire(
                "logbook_entry",
                {
                    "name": self.name or self._config_entry.title,
                    "message": f"Fan mode changed: {previous_fan_mode} -> {current_fan_mode}",
                    "entity_id": self.entity_id,
                    "domain": DOMAIN,
                },
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self.client.set_temperature(int(temperature))