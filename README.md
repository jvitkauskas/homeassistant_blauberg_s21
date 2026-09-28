# Blauberg S21 for Home Assistant

Control a Blauberg S21 ventilation unit locally over Modbus TCP. Requires
**Home Assistant 2026.9.4 or newer** (Python 3.14.2+) and uses `pybls21==5.1.0`.

## Installation

Install with HACS, or copy `custom_components/blauberg_s21` into your Home
Assistant `config/custom_components` directory and restart Home Assistant.
In **Settings → Devices & services → Add integration**, select **Blauberg S21**
and wait for a short network search. Choose a discovered device, then confirm
its host and Modbus port (normally 502). You can also enter the connection
manually; if nothing is found, the manual form opens automatically.

Discovery searches the IPv4 interfaces enabled in Home Assistant's network
settings, using UDP port 4000. It normally works only within the local subnet.
Blocked broadcasts, network isolation, or firmware without discovery support
can prevent results; manual setup remains available. Discovery runs when you
start adding the integration, not continuously in the background. It does not
write device settings or require a discovery password on the tested S21.

The selected controller ID is rechecked and Modbus connectivity is validated
before saving. Manual setup also attempts to read the ID, but accepts devices
that support only Modbus. The integration stores a discovered controller ID to
detect duplicates across host/IP changes; it does not replace entity IDs.

The climate entity supports power, HVAC mode, target temperature, and fan mode.
Three-speed devices use low/medium/high labels; other devices expose numbered
levels. `custom` selects manual fan mode. The displayed current temperature is
the supply outlet temperature, not necessarily the room temperature. The climate
entity does not report heating/cooling activity: pybls21 5.1.0 infers that value
rather than exposing measured heater/cooler operation. The selected HVAC mode
and temperature target remain available.

## Sensors and controls

All readings share the climate entity's poll; adding sensors does not multiply
network requests. The integration exposes:

- Supply, intake, extract, and exhaust temperatures; humidity, airflow, and duct
  pressure where available.
- Supply/extract fan **RPM**, and separate optional fan-performance percentages.
- Remaining filter-service time in hours, including the device's day/hour/minute
  components; timer duration and accumulated operating time.
- “Filter needs attention” and “Problem” binary sensors, plus alarm severity with
  active numeric codes in the `alarm_codes` attribute. Raw filter status remains
  available as a diagnostic sensor.
- Optional bypass position or rotor control-position reading, only when fitted.
- Buttons to reset the filter timer and alarms.
- Timer and weekly-schedule switches; an optional read-only “Boost active” sensor.
  The previous proposed boost switch wrote the external boost-input enable flag
  while reading a different active-state flag, so it is no longer exposed.
- A manual fan-percentage slider, which sets the configured percentage and then
  selects manual fan mode (255).
- A bypass/rotor mode selector when fitted, and a manual-position slider only
  for analogue bypass/rotor hardware.

RPM, exhaust temperature, timer controls, boost status, and other optional
engineering readings are disabled by default for new entities. Enable them in
the entity registry if useful. Existing user choices are preserved. All entities
belong to one physical S21 device; the climate entity remains its primary control. A successful
Modbus response can still contain an unavailable value: `0xFFFF` percentages and
faulty temperature sensors show as unknown, not as zero or an extreme reading.
Valid zero readings stay zero.

Timer/schedule switches toggle settings already configured on the unit; they do
not edit schedules or timer durations. The filter-reset button restarts the
existing interval; **changing that interval is not yet implemented**.

Filter attention uses the controller's IR31 status: 0 means clean; 1 means the
intake filter is clogged; 2 means the extract filter is clogged; 3 means both
filters are clogged or the replacement timer has expired. The combined state 3
cannot distinguish those causes. A zero countdown alone does not indicate a
problem. The Problem sensor includes both alarms and warnings (IR38); unknown
status values remain unknown instead of appearing healthy.

Bypass controls display Closed/Open/Automatic for discrete hardware and
Closed/Manual/Automatic for analogue hardware. Rotor controls display
Running/Stopped/Automatic or Running/Manual/Automatic, respectively. Stored
select values stay `closed`, `open`, and `auto` for existing automations.

The analogue rotor's manual-speed slider uses 0% = stopped and 100% = maximum
speed. The integration converts to the device's reversed control scale. The
bypass slider retains 0% = closed and 100% = open. Setting either percentage does
not implicitly change the mode; choose Manual to apply the manual setting.
The optional rotor control-position sensor remains the raw IR51 percentage;
its meaning as actual rotor speed has not been verified. Reload the integration
if the installed bypass/rotor hardware type changes.

If you installed an earlier PR build, the analogue rotor number keeps its entity
ID but now uses the reversed, speed-oriented scale: convert old automation
values with `100 - old_value`. This affects analogue rotors only. The misleading
boost switch is replaced by a separate read-only sensor.

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
Reconfiguration also reads the controller ID. If the entry already has an ID,
the new endpoint must report the same one; allow UDP port 4000 for this check.
Older entries without an ID learn it after a successful reconfiguration, while
retaining their config entry and registered entities. Devices already configured
at the same host/port are rejected even when no ID is available. Aliases cannot
be reliably matched against older entries until those entries have learned an ID.
IP address changes are not automatically applied; use Reconfigure to update them.

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
