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

## Sensors and controls

All readings share the climate entity's poll; adding sensors does not multiply
network requests. The integration exposes:

- Supply, intake, extract, and exhaust temperatures; humidity, airflow, and duct
  pressure where available.
- Supply/extract fan **RPM**, and separate optional fan-performance percentages.
- Remaining filter-service time in hours, including the device's day/hour/minute
  components; timer duration and accumulated operating time.
- Alarm severity with active numeric codes in the `alarm_codes` attribute, raw
  filter-status code, and optional bypass/rotor position.
- Buttons to reset the filter timer and alarms.
- Timer and weekly-schedule switches; an optional boost switch.
- A manual fan-percentage slider, which sets the configured percentage and then
  selects manual fan mode (255).
- A bypass/rotor mode selector when fitted, and a manual-position slider only
  for analogue bypass/rotor hardware.

Optional/diagnostic sensors and boost are disabled by default where appropriate;
enable them in the entity registry if your device supports them. A successful
Modbus response can still contain an unavailable value: `0xFFFF` percentages and
faulty temperature sensors show as unknown, not as zero or an extreme reading.
Valid zero readings stay zero.

Timer/schedule switches toggle settings already configured on the unit; they do
not edit schedules or timer durations. The filter-reset button restarts the
existing interval; **changing that interval is not yet implemented**.

For bypass/rotor controls, closed means bypass closed / rotor running; open means
bypass open / discrete rotor stopped, or manual control for analogue hardware.
Setting a manual position does not change the mode. Position 0 means closed
bypass / maximum rotor speed; 100 means open bypass / stopped rotor. Reload the
integration if the installed bypass/rotor type is changed on the controller.

Every successful control fetches confirmed device state. Downloads from the
integration's **Diagnostics** menu contain cached device readings and update
status, without host, port, config-entry identifiers, or user configuration.
Diagnostics make no extra device request.

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

The sensor, maintenance-button, and manual-fan-control designs adapt the work in
[@birdie1's PR #15](https://github.com/jvitkauskas/homeassistant_blauberg_s21/pull/15),
with attribution retained in this README and the commit co-author credit. The
implementation uses pybls21 5 snapshots and confirmed updates rather than
embedding a modified Modbus client in the integration.
