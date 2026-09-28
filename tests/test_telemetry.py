"""Sensor semantics, capability-aware controls, and shared updates."""

import json
from dataclasses import replace
from datetime import timedelta
from unittest.mock import call

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pybls21 import BypassMode, BypassType, ModbusCommunicationException

from custom_components.blauberg_s21.const import DOMAIN
from custom_components.blauberg_s21.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.blauberg_s21.number import S21Percentage
from custom_components.blauberg_s21.select import S21BypassMode
from custom_components.blauberg_s21.sensor import SENSORS, S21Sensor
from custom_components.blauberg_s21.switch import SWITCHES, S21Switch


def entity_id(hass, entry, platform, key):
    return er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )


async def test_all_sensors_share_one_poll_and_preserve_units(
    hass, entry, client, snapshot
):
    client.poll.return_value = replace(
        snapshot,
        current_extract_temperature=21.9,
        current_exhaust_temperature=21.5,
        supply_fan_speed_percent=None,
        extract_fan_speed_percent=0,
        filter_countdown_days=2,
        filter_countdown_hours=3,
        filter_countdown_minutes=30,
        timer_countdown=timedelta(minutes=2),
        operating_time_minutes=12345,
        alarm_codes=(23, 40),
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client.poll.assert_awaited_once()
    sensors = {
        description.key: S21Sensor(entry, description) for description in SENSORS
    }
    values = {key: sensor.native_value for key, sensor in sensors.items()}
    assert len(values) == 19
    assert values["supply_fan_speed"] == 1380
    assert sensors["supply_fan_speed"].native_unit_of_measurement == "rpm"
    assert values["supply_fan_speed_percent"] is None
    assert values["extract_fan_speed_percent"] == 0
    assert values["filter_remaining"] == 51.5
    assert values["timer_countdown"] == 120
    assert values["operating_time_minutes"] == 12345
    assert values["alarm_state"] == "warning"
    assert sensors["alarm_state"].extra_state_attributes == {"alarm_codes": [23, 40]}
    assert sensors["current_temperature"].extra_state_attributes is None
    assert (
        hass.states.get(entity_id(hass, entry, "sensor", "filter_remaining")).state
        == "51.5"
    )
    for description in SENSORS:
        registered = er.async_get(hass).async_get(
            entity_id(hass, entry, "sensor", description.key)
        )
        assert bool(registered.disabled) == (
            not description.entity_registry_enabled_default
        )
    entry.runtime_data.async_set_updated_data(
        replace(
            client.poll.return_value, filter_countdown_days=None, timer_countdown=None
        )
    )
    assert sensors["filter_remaining"].native_value is None
    assert sensors["timer_countdown"].native_value is None
    client.poll.side_effect = ModbusCommunicationException("offline")
    await entry.runtime_data.async_refresh()
    assert all(not sensor.available for sensor in sensors.values())
    assert (
        hass.states.get(entity_id(hass, entry, "sensor", "filter_remaining")).state
        == "unavailable"
    )


@pytest.mark.parametrize(
    ("key", "method"),
    [
        ("reset_alarm", "reset_alarm"),
        ("reset_filter_change_timer", "reset_filter_change_timer"),
    ],
)
async def test_maintenance_buttons(hass, entry, client, key, method):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": entity_id(hass, entry, "button", key)},
        blocking=True,
    )
    getattr(client, method).assert_awaited_once_with()
    assert client.poll.await_count == 2


@pytest.mark.parametrize(
    ("key", "on_method", "off_method", "field"),
    [
        ("boost", "boost_on", "boost_off", "is_boosting"),
        ("timer", "set_timer_on", "set_timer_off", "is_timer"),
        (
            "schedule",
            "set_scheduler_mode_on",
            "set_scheduler_mode_off",
            "is_schedule_mode",
        ),
    ],
)
async def test_switches_refresh_from_device(
    hass, entry, client, snapshot, key, on_method, off_method, field
):
    await hass.config_entries.async_setup(entry.entry_id)
    description = next(d for d in SWITCHES if d.key == key)
    switch = S21Switch(entry, description)
    assert not switch.is_on
    client.poll.return_value = replace(snapshot, **{field: True})
    await switch.async_turn_on()
    getattr(client, on_method).assert_awaited_once_with()
    assert switch.is_on
    client.poll.return_value = snapshot
    await switch.async_turn_off()
    getattr(client, off_method).assert_awaited_once_with()
    assert not switch.is_on
    assert client.poll.await_count == 3


async def test_manual_fan_percentage_confirms_configured_value(
    hass, entry, client, snapshot
):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client.poll.return_value = replace(
        snapshot,
        manual_fan_speed_percent=42,
        fan_mode=255,
        supply_fan_speed_percent=None,
    )
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": entity_id(hass, entry, "number", "manual_fan_speed_percent"),
            "value": 42,
        },
        blocking=True,
    )
    assert client.mock_calls[-3:] == [
        call.set_manual_fan_speed_percent(42),
        call.set_fan_mode(255),
        call.poll(),
    ]
    assert (
        hass.states.get(
            entity_id(hass, entry, "number", "manual_fan_speed_percent")
        ).state
        == "42"
    )
    assert hass.states.get("climate.blauberg_s21").attributes["fan_mode"] == "custom"
    number = S21Percentage(entry, "manual_fan_speed_percent")
    for value in (-1.0, 100.1, 10.5, float("nan"), True):
        with pytest.raises(ServiceValidationError):
            await number.async_set_native_value(value)


@pytest.mark.parametrize("bypass_type", list(BypassType))
async def test_bypass_controls_follow_installed_hardware(
    hass, entry, client, snapshot, bypass_type
):
    client.poll.return_value = replace(
        snapshot,
        bypass_type=bypass_type,
        bypass_mode=BypassMode.AUTO,
        manual_bypass_position=60,
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    selector_id = entity_id(hass, entry, "select", "bypass_mode")
    number_id = entity_id(hass, entry, "number", "manual_bypass_position")
    assert bool(selector_id) == (bypass_type != BypassType.NOT_AVAILABLE)
    assert bool(number_id) == (
        bypass_type in (BypassType.BYPASS_ANALOGUE, BypassType.ROTOR_ANALOGUE)
    )
    if selector_id:
        selector = S21BypassMode(entry)
        assert selector.current_option == "auto"
        client.poll.return_value = replace(
            client.poll.return_value, bypass_mode=BypassMode.OPEN
        )
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": selector_id, "option": "open"},
            blocking=True,
        )
        client.set_bypass_mode.assert_awaited_once_with(BypassMode.OPEN)
        assert hass.states.get(selector_id).state == "open"
        with pytest.raises(ServiceValidationError):
            await selector.async_select_option("invalid")
        entry.runtime_data.async_set_updated_data(
            replace(client.poll.return_value, bypass_mode=None)
        )
        assert selector.current_option is None
    if number_id:
        client.poll.return_value = replace(
            client.poll.return_value, manual_bypass_position=30
        )
        await hass.services.async_call(
            "number", "set_value", {"entity_id": number_id, "value": 30}, blocking=True
        )
        client.set_bypass_position.assert_awaited_once_with(30)
        assert hass.states.get(number_id).state == "30"
        # Setting the manual percentage does not change mode implicitly.
        assert client.set_bypass_mode.await_count == 1


@pytest.mark.parametrize("duration", [None, timedelta(seconds=15)])
async def test_diagnostics_are_json_serializable_without_connection_data(
    hass, entry, client, snapshot, duration
):
    client.poll.return_value = replace(snapshot, timer_countdown=duration)
    await hass.config_entries.async_setup(entry.entry_id)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    encoded = json.dumps(diagnostics)
    assert "s21.local" not in encoded
    assert entry.entry_id not in encoded
    assert diagnostics["last_update_success"]
    assert diagnostics["cached_device"]["timer_countdown_seconds"] == (
        15 if duration else None
    )
    client.poll.assert_awaited_once()
