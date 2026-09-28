"""Setup, availability, service calls, and registry migration."""

from dataclasses import replace

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pybls21 import HVACMode, ModbusCommunicationException, UnsupportedDeviceException
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blauberg_s21 import async_migrate_entry
from custom_components.blauberg_s21.climate import BlS21ClimateEntity
from custom_components.blauberg_s21.const import DOMAIN


async def test_setup_poll_once_and_unload(hass, entry, client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client.poll.assert_awaited_once()
    entity = hass.states.get("climate.blauberg_s21")
    assert entity.state == "fan_only"
    assert entity.attributes["current_temperature"] == 22.6
    assert entity.attributes["fan_modes"] == ["low", "medium", "high", "custom"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.NOT_LOADED


async def test_setup_retry(hass, entry, client):
    client.poll.side_effect = ModbusCommunicationException("offline")
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_availability_recovery(hass, entry, client, snapshot):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client.poll.side_effect = ModbusCommunicationException("offline")
    await entry.runtime_data.async_refresh()
    assert hass.states.get("climate.blauberg_s21").state == "unavailable"
    client.poll.side_effect = None
    client.poll.return_value = replace(
        snapshot, current_temperature=None, hvac_action=None
    )
    await entry.runtime_data.async_refresh()
    state = hass.states.get("climate.blauberg_s21")
    assert state.state == "fan_only"
    assert state.attributes["current_temperature"] is None
    assert state.attributes["hvac_action"] == "fan"


@pytest.mark.parametrize(
    ("service", "data", "method", "args"),
    [
        ("set_hvac_mode", {"hvac_mode": "heat"}, "set_hvac_mode", (HVACMode.HEAT,)),
        ("set_fan_mode", {"fan_mode": "custom"}, "set_fan_mode", (255,)),
        ("set_temperature", {"temperature": 22}, "set_temperature", (22,)),
        ("turn_on", {}, "turn_on", ()),
        ("turn_off", {}, "turn_off", ()),
    ],
)
async def test_commands_refresh_confirmed_state(
    hass, entry, client, snapshot, service, data, method, args
):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client.poll.return_value = replace(
        snapshot, hvac_mode=HVACMode.HEAT, fan_mode=255, target_temperature=22
    )
    await hass.services.async_call(
        "climate", service, {"entity_id": "climate.blauberg_s21", **data}, blocking=True
    )
    getattr(client, method).assert_awaited_once_with(*args)
    assert client.poll.await_count == 2
    state = hass.states.get("climate.blauberg_s21")
    assert state.state == "heat"
    assert state.attributes["temperature"] == 22
    assert state.attributes["fan_mode"] == "custom"


async def test_write_error_marks_unavailable(hass, entry, client):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client.turn_off.side_effect = ModbusCommunicationException("offline")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "climate", "turn_off", {"entity_id": "climate.blauberg_s21"}, blocking=True
        )
    assert hass.states.get("climate.blauberg_s21").state == "unavailable"


async def test_invalid_values_and_five_level_fans(hass, entry, client, snapshot):
    client.poll.return_value = replace(
        snapshot, max_fan_level=5, fan_modes=(1, 2, 3, 4, 5, 255), fan_mode=5
    )
    await hass.config_entries.async_setup(entry.entry_id)
    climate = BlS21ClimateEntity(entry)
    assert climate.fan_modes == ["1", "2", "3", "4", "5", "custom"]
    assert climate.fan_mode == "5"
    for value in (21.5, float("nan"), True, "21"):
        with pytest.raises(ServiceValidationError):
            await climate.async_set_temperature(temperature=value)
    for value in ("bad", "6"):
        with pytest.raises(ServiceValidationError):
            await climate.async_set_fan_mode(value)
    with pytest.raises(ServiceValidationError):
        await climate.async_set_hvac_mode("invalid")
    client.set_temperature.assert_not_called()
    await climate.async_set_temperature()
    client.set_fan_mode.side_effect = ValueError("bad value")
    with pytest.raises(ServiceValidationError):
        await climate.async_set_fan_mode("4")
    assert climate.available
    entry.runtime_data.async_set_updated_data(replace(snapshot, fan_mode=None))
    assert climate.fan_mode is None


@pytest.mark.parametrize("unique_id", [None, "S21_s21.local_502", "legacy-id"])
async def test_migrate_preserves_entity_and_device(hass, unique_id):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "s21.local", "port": 502},
        unique_id=unique_id,
        version=1,
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    devices = dr.async_get(hass)
    device = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, unique_id or "S21_s21.local_502")},
        name="Ventilation",
    )
    entity = registry.async_get_or_create(
        "climate",
        DOMAIN,
        unique_id or "S21_s21.local_502",
        config_entry=entry,
        device_id=device.id,
        suggested_object_id="existing_ventilation",
    )
    registry.async_update_entity(entity.entity_id, name="My ventilation")
    assert await async_migrate_entry(hass, entry)
    migrated = registry.async_get(entity.entity_id)
    assert migrated.unique_id == f"{entry.entry_id}_climate"
    assert migrated.name == "My ventilation"
    assert migrated.device_id == device.id
    assert devices.async_get(device.id).identifiers == {(DOMAIN, entry.entry_id)}
    assert entry.version == 2
    assert entry.unique_id is None
    assert await async_migrate_entry(hass, entry)


async def test_future_version_is_not_migrated(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=3)
    assert not await async_migrate_entry(hass, entry)


async def test_unsupported_device_is_a_permanent_setup_error(hass, entry, client):
    client.poll.side_effect = UnsupportedDeviceException("wrong device")
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_ERROR
