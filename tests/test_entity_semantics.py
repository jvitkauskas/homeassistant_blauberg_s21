"""User-facing status, hardware-specific labels, and entity defaults."""

from dataclasses import replace

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pybls21 import (
    BypassMode,
    BypassType,
    HVACAction,
    HVACMode,
    ModbusCommunicationException,
)

from custom_components.blauberg_s21.number import S21Percentage
from custom_components.blauberg_s21.select import S21BypassMode
from custom_components.blauberg_s21.sensor import SENSORS, S21Sensor
from tests.test_telemetry import entity_id


@pytest.mark.parametrize(
    "raw,expected", [(0, "off"), (1, "on"), (2, "on"), (3, "on"), (65535, "unknown")]
)
async def test_filter_status_not_inferred_from_countdown(
    hass, entry, client, snapshot, raw, expected
):
    client.poll.return_value = replace(
        snapshot,
        filter_state=raw,
        filter_countdown_days=0,
        filter_countdown_hours=0,
        filter_countdown_minutes=0,
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    identifier = entity_id(hass, entry, "binary_sensor", "filter_attention")
    state = hass.states.get(identifier)
    assert state.state == expected
    assert state.attributes["device_class"] == "problem"
    client.poll.assert_awaited_once()
    client.poll.side_effect = ModbusCommunicationException("offline")
    await entry.runtime_data.async_refresh()
    assert hass.states.get(identifier).state == "unavailable"


@pytest.mark.parametrize(
    "raw,expected", [(0, "off"), (1, "on"), (2, "on"), (65535, "unknown")]
)
async def test_problem_includes_warnings(hass, entry, client, snapshot, raw, expected):
    client.poll.return_value = replace(snapshot, alarm_state=raw)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, entry, "binary_sensor", "problem")).state
        == expected
    )


@pytest.mark.parametrize(
    "mode,action",
    [
        (HVACMode.HEAT, HVACAction.HEATING),
        (HVACMode.COOL, HVACAction.COOLING),
        (HVACMode.AUTO, HVACAction.IDLE),
    ],
)
async def test_inferred_hvac_action_is_not_advertised(
    hass, entry, client, snapshot, mode, action
):
    client.poll.return_value = replace(snapshot, hvac_mode=mode, hvac_action=action)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("climate.blauberg_s21")
    assert state.state == mode.value
    assert "hvac_action" not in state.attributes
    assert state.attributes["current_temperature"] == snapshot.current_temperature


@pytest.mark.parametrize(
    "hardware,translation",
    [
        (BypassType.BYPASS_TWO_POINT, "bypass_mode"),
        (BypassType.BYPASS_THREE_POINT, "bypass_mode"),
        (BypassType.BYPASS_ANALOGUE, "bypass_analogue_mode"),
        (BypassType.ROTOR_DISCRETE, "rotor_mode"),
        (BypassType.ROTOR_ANALOGUE, "rotor_analogue_mode"),
    ],
)
async def test_hardware_labels_keep_stored_option_values(
    hass, entry, client, snapshot, hardware, translation
):
    client.poll.return_value = replace(
        snapshot, bypass_type=hardware, bypass_mode=BypassMode.AUTO
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    select = S21BypassMode(entry)
    assert select.translation_key == translation
    assert select.options == ["closed", "open", "auto"]
    assert select.unique_id == f"{entry.entry_id}_bypass_mode"
    description = next(d for d in SENSORS if d.key == "bypass_position")
    sensor = S21Sensor(entry, description)
    assert sensor.translation_key == (
        "rotor_position"
        if hardware in (BypassType.ROTOR_DISCRETE, BypassType.ROTOR_ANALOGUE)
        else "bypass_position"
    )


@pytest.mark.parametrize("speed,raw", [(0.0, 100), (30.0, 70), (100.0, 0)])
async def test_rotor_speed_reverses_device_scale(
    hass, entry, client, snapshot, speed, raw
):
    client.poll.return_value = replace(
        snapshot, bypass_type=BypassType.ROTOR_ANALOGUE, manual_bypass_position=raw
    )
    await hass.config_entries.async_setup(entry.entry_id)
    number = S21Percentage(entry, "manual_bypass_position")
    assert number.translation_key == "manual_rotor_speed"
    assert number.native_value == speed
    await number.async_set_native_value(speed)
    client.set_bypass_position.assert_awaited_once_with(raw)
    client.set_bypass_mode.assert_not_called()
    entry.runtime_data.async_set_updated_data(
        replace(client.poll.return_value, manual_bypass_position=None)
    )
    assert number.native_value is None


async def test_grouping_defaults_and_user_overrides(hass, entry, client):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    assert all(e.device_id == devices[0].id for e in entries)
    for platform, key in [
        ("sensor", "supply_fan_speed"),
        ("sensor", "extract_fan_speed"),
        ("sensor", "current_exhaust_temperature"),
        ("switch", "timer"),
        ("binary_sensor", "boost_active"),
    ]:
        assert (
            registry.async_get(entity_id(hass, entry, platform, key)).disabled_by
            == er.RegistryEntryDisabler.INTEGRATION
        )
    for key in ["filter_attention", "problem"]:
        assert not registry.async_get(
            entity_id(hass, entry, "binary_sensor", key)
        ).disabled
    assert entity_id(hass, entry, "switch", "boost") is None
    rpm = entity_id(hass, entry, "sensor", "supply_fan_speed")
    registry.async_update_entity(rpm, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert not registry.async_get(rpm).disabled
    assert hass.states.get(rpm).state == "1380"
