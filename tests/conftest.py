"""Fixtures using Home Assistant's actual test framework and a mocked device."""

from unittest.mock import MagicMock, patch

import pytest
from pybls21 import ClimateDevice, HVACAction, HVACMode, S21Client
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blauberg_s21.const import DOMAIN


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Load the custom component in the test Home Assistant instance."""


@pytest.fixture
def snapshot():
    return ClimateDevice(
        available=True,
        name="Blauberg S21",
        temperature_unit="°C",
        precision=1,
        current_temperature=22.6,
        target_temperature=21,
        target_temperature_step=1,
        min_temp=15,
        max_temp=30,
        current_humidity=None,
        hvac_mode=HVACMode.FAN_ONLY,
        hvac_action=HVACAction.FAN,
        hvac_modes=tuple(HVACMode),
        fan_mode=2,
        fan_modes=(1, 2, 3, 255),
        manufacturer="Blauberg",
        model="S21",
        sw_version="0.36",
        is_boosting=False,
        current_intake_temperature=16.5,
        manual_fan_speed_percent=50,
        max_fan_level=3,
        filter_state=3,
        alarm_state=2,
        supply_fan_speed=1380,
        extract_fan_speed=1320,
    )


@pytest.fixture
def client(snapshot):
    client = MagicMock(spec=S21Client)
    client.poll.return_value = snapshot
    with (
        patch("custom_components.blauberg_s21.S21Client", return_value=client),
        patch(
            "custom_components.blauberg_s21.config_flow.S21Client", return_value=client
        ),
    ):
        yield client


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Blauberg S21",
        data={"host": "s21.local", "port": 502},
        version=2,
        minor_version=1,
    )
    entry.add_to_hass(hass)
    return entry
