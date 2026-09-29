"""Check the actual translations returned to the Home Assistant frontend."""

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.helpers.translation import async_get_translations
from pybls21 import DiscoveredDevice

from custom_components.blauberg_s21.const import DOMAIN


@pytest.mark.parametrize(
    "language, labels",
    [
        ("en", ["Choose a discovered device", "Enter connection manually"]),
        ("de", ["Ein gefundenes Gerät auswählen", "Verbindung manuell eingeben"]),
        ("lt", ["Pasirinkti rastą įrenginį", "Įvesti ryšio duomenis rankiniu būdu"]),
        ("fr", ["Choose a discovered device", "Enter connection manually"]),
    ],
)
async def test_setup_menu_translations(hass, discovery, language, labels):
    discovery[0].return_value = (
        DiscoveredDevice(host="192.168.1.149", device_id="0024005433375107"),
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    translations = await async_get_translations(hass, language, "config", {DOMAIN})
    prefix = (
        f"component.{result['handler']}.config.step.{result['step_id']}.menu_options"
    )
    assert [
        translations[f"{prefix}.{option}"] for option in result["menu_options"]
    ] == labels
