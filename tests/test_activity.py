"""Reported activity drives HA state independently of mode and temperatures."""

from dataclasses import replace

import pytest
from homeassistant.helpers import entity_registry as er
from pybls21 import HVACAction, HVACMode, ModbusCommunicationException

from custom_components.blauberg_s21.diagnostics import (
    async_get_config_entry_diagnostics,
)
from tests.test_telemetry import entity_id


@pytest.mark.parametrize(
    "mode,heating,cooling,supply_rpm,extract_rpm,expected",
    [
        (HVACMode.HEAT, False, False, 0, 0, "idle"),
        (HVACMode.COOL, False, False, 0, 0, "idle"),
        (HVACMode.AUTO, False, False, 0, 0, "idle"),
        (HVACMode.FAN_ONLY, False, False, 0, 0, "idle"),
        (HVACMode.OFF, False, False, 0, 0, "off"),
        (HVACMode.HEAT, True, False, 1200, 1200, "heating"),
        (HVACMode.COOL, False, True, 1200, 1200, "cooling"),
        (HVACMode.AUTO, True, False, 1200, 1200, "heating"),
        (HVACMode.AUTO, False, True, 1200, 1200, "cooling"),
        # Observe the controller even during mode transitions/run-on.
        (HVACMode.OFF, True, False, 1200, 1200, "heating"),
        (HVACMode.FAN_ONLY, False, True, 1200, 1200, "cooling"),
        (HVACMode.HEAT, False, False, 1200, 0, "fan"),
        (HVACMode.COOL, False, False, 0, 1200, "fan"),
        (HVACMode.OFF, False, False, 0, 1200, "fan"),
        (HVACMode.AUTO, True, True, 1200, 1200, None),
        (HVACMode.AUTO, None, False, 1200, 1200, None),
        (HVACMode.AUTO, False, None, 1200, 1200, None),
        (HVACMode.AUTO, True, None, 1200, 1200, None),
        (HVACMode.AUTO, None, True, 1200, 1200, None),
    ],
)
async def test_reported_climate_activity(
    hass,
    entry,
    client,
    snapshot,
    mode,
    heating,
    cooling,
    supply_rpm,
    extract_rpm,
    expected,
):
    client.poll.return_value = replace(
        snapshot,
        hvac_mode=mode,
        is_heating=heating,
        is_cooling=cooling,
        supply_fan_speed=supply_rpm,
        extract_fan_speed=extract_rpm,
        # Neither this legacy inference nor unavailable temperatures controls action.
        hvac_action=HVACAction.HEATING,
        current_temperature=None,
        current_intake_temperature=None,
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("climate.blauberg_s21")
    assert state.state == mode.value
    assert state.attributes.get("hvac_action") == expected
    client.poll.assert_awaited_once()


async def test_activity_sensors_share_updates_and_report_unknown_unavailable(
    hass, entry, client, snapshot
):
    client.poll.return_value = replace(snapshot, is_heating=True, is_cooling=True)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    identifiers = [
        entity_id(hass, entry, "binary_sensor", key)
        for key in ("heating_active", "cooling_active")
    ]
    for identifier in identifiers:
        assert (
            registry.async_get(identifier).disabled_by
            == er.RegistryEntryDisabler.INTEGRATION
        )
        registry.async_update_entity(identifier, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert client.poll.await_count == 2
    assert [hass.states.get(identifier).state for identifier in identifiers] == [
        "on",
        "on",
    ]
    assert hass.states.get("climate.blauberg_s21").attributes.get("hvac_action") is None
    client.poll.return_value = replace(snapshot, is_heating=False, is_cooling=None)
    await entry.runtime_data.async_refresh()
    assert [hass.states.get(identifier).state for identifier in identifiers] == [
        "off",
        "unknown",
    ]
    client.poll.side_effect = ModbusCommunicationException("offline")
    await entry.runtime_data.async_refresh()
    for identifier in [*identifiers, "climate.blauberg_s21"]:
        assert hass.states.get(identifier).state == "unavailable"
    client.poll.side_effect = None
    client.poll.return_value = replace(snapshot, is_heating=False, is_cooling=False)
    await entry.runtime_data.async_refresh()
    assert [hass.states.get(identifier).state for identifier in identifiers] == [
        "off",
        "off",
    ]
    assert hass.states.get("climate.blauberg_s21").attributes["hvac_action"] == "fan"


async def test_diagnostics_distinguish_raw_bits_and_legacy_inference(
    hass, entry, client, snapshot
):
    client.poll.return_value = replace(
        snapshot, hvac_action=HVACAction.HEATING, is_heating=False, is_cooling=False
    )
    await hass.config_entries.async_setup(entry.entry_id)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    data = diagnostics["cached_device"]
    assert data["is_heating"] is False
    assert data["is_cooling"] is False
    assert "hvac_action" not in data
    assert data["legacy_inferred_hvac_action"] == "heating"
    client.poll.assert_awaited_once()
