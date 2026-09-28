# Blauberg S21 for Home Assistant

Control a Blauberg S21 ventilation unit locally over Modbus TCP. Requires
**Home Assistant 2026.9.4 or newer** (Python 3.14.2+) and uses `pybls21==5.0.0`.

## Installation

Install with HACS, or copy `custom_components/blauberg_s21` into your Home
Assistant `config/custom_components` directory and restart Home Assistant.
In **Settings → Devices & services → Add integration**, select **Blauberg S21**
and enter the device host and Modbus port (normally 502).

The climate entity supports power, HVAC mode, target temperature, and fan mode.
Three-speed devices use low/medium/high labels; other devices expose numbered
levels. `custom` selects manual fan mode. The displayed current temperature is
the supply outlet temperature, not necessarily the room temperature. HVAC action
is inferred from the configured mode and supply temperatures.

## Updates, errors, and reconfiguration

The integration polls once every 30 seconds and shares that snapshot between
entities. Successful controls perform a confirming poll immediately. Network
failures mark entities unavailable; polling automatically retries. Each poll or
command is bounded by a 20-second deadline, including waiting for other work.

Use **Reconfigure** on the integration to change its host or port. The connection
is validated before saving. Entity and device identity uses the config entry, so
changing the IP address preserves the registered entities and their settings.
Hostnames are compared without case and surrounding spaces when checking for
duplicates; aliases referring to the same device cannot be detected without a
hardware identifier.

## Upgrading from 0.4.x

Update Home Assistant before installing this version. Existing config entries
migrate their entity/device registry identifiers in place: entity IDs, custom
names, and device associations are retained. Do not remove and re-add the
integration to perform this migration. The domain remains `blauberg_s21`.

These migrations cover releases from this repository, not the differently named
`blauberg_s21_ext` fork or other forks with their own entity layouts.

## Development

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-test.txt
ruff check .
ruff format --check .
mypy
pytest -q
```

Tests use Home Assistant's actual custom-component test framework and a mocked
client. No real device is contacted. CI runs tests, strict typing, formatting,
HACS validation, and hassfest; test coverage must stay at or above 95%.

The shared-coordinator approach builds on the direction proposed by
[Jonas Vogel (@birdie1) in PR #15](https://github.com/jvitkauskas/homeassistant_blauberg_s21/pull/15).
Protocol handling remains in the independently tested
[pybls21 library](https://github.com/jvitkauskas/pybls21).
