# Blauberg S21 for Home Assistant

Control a Blauberg S21 ventilation unit locally over Modbus TCP. Requires
**Home Assistant 2026.9.4 or newer** (Python 3.14.2+) and uses `pybls21==5.2.0`.

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

When confirming a discovered device at its discovered IP address, setup reuses
the controller ID from that discovery response and validates Modbus connectivity
before saving. It does not require a second UDP response. If you change the host
in the confirmation form, setup verifies that the new endpoint has the selected
controller ID. Manual setup also attempts to read the ID, but accepts devices
that support only Modbus. The integration stores a discovered controller ID to
detect duplicates across host/IP changes; it does not replace entity IDs.

The climate entity supports power, HVAC mode, target temperature, and fan mode.
Three-speed devices use low/medium/high labels; other devices expose numbered
levels. `custom` selects manual fan mode. The displayed current temperature is
the supply outlet temperature, not necessarily the room temperature. The climate
entity reports heating/cooling activity from the controller's DI7/DI8 operation
bits. When both are inactive, measured fan RPM distinguishes ventilation from
idle (or off when the unit is disabled and the fans have stopped). Selected mode
and temperature differences never imply that a heater/cooler is running. Missing
bits or simultaneous heating and cooling leave the combined activity unknown.
Activity can differ from the selected mode, for example while fans run after
switching the unit off.

Optional “Heating active” and “Cooling active” binary sensors expose the bits
individually, including simultaneous activity. They share the existing poll and
are disabled by default. These indications describe controller-reported
operation, not independently measured electrical power. Poll failures make the
climate entity and sensors unavailable; neither the UI nor diagnostics uses the
library's legacy inferred activity as a measurement.

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

RPM, exhaust temperature, timer controls, boost/heater/cooler status, and other optional
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
python scripts/check_metadata.py
python -m unittest discover -s scripts -p 'test_*.py' -v
ruff check .
ruff format --check .
mypy
pytest -q
```

Tests use Home Assistant's actual custom-component test framework and a mocked
client. No real device is contacted. CI runs tests, strict typing, formatting,
HACS validation, and hassfest; test coverage must stay at or above 95%.

The test matrix covers Python 3.14.2 and the latest 3.14 patch with the pinned
Home Assistant 2026.9.4 baseline. A third job resolves the newest compatible
Home Assistant/test-framework pair on Python 3.14 using
`requirements-compatibility.txt`. It does not replace the pinned baseline.
All three jobs run on PRs, main, version tags, a weekly schedule, and manual
dispatch. The logs report the exact Home Assistant, framework, and library
versions tested. HACS and hassfest also run daily against their upstream validators.
To reproduce the compatibility job, install `requirements-compatibility.txt`
with `pip install --upgrade` in a separate virtual environment, then run
`python scripts/check_metadata.py --ha-channel latest` and the checks above
(omit the baseline-only `python scripts/check_metadata.py` command).

Runtime dependencies used by both test environments live in
`requirements-common.txt`; CI checks them against the integration manifest and
the installed packages. The pinned test framework must install exactly the
minimum HA version declared in `hacs.json`. Update those together when raising
the minimum version. Dependabot checks GitHub Actions versions weekly.

## Releases

Keep the manifest version at the next intended release while PRs are pending;
merging a PR does not create a tag or publish a release.

After merging the release's changes into main, open **Actions → Release → Run
workflow**, choose **main**, and enter the manifest version prefixed with `v`
(currently `v0.6.2`). The workflow checks the tag/version match and runs the
complete test matrix, HACS validation, and hassfest before creating the GitHub
tag and release with generated release notes. It releases the exact commit
selected when the workflow starts, even if main advances while checks run.
Only the final publishing job has repository write permission. An existing tag
pointing at another commit is rejected; tags are never moved.

Use this workflow instead of publishing manually so validation happens before
the release becomes available. Checks also run for manually pushed version
tags, but cannot prevent a release created outside this workflow. HACS installs
GitHub releases; this integration does not need a PyPI publishing job.

The shared-coordinator approach builds on the direction proposed by
[Jonas Vogel (@birdie1) in PR #15](https://github.com/jvitkauskas/homeassistant_blauberg_s21/pull/15).
Protocol handling remains in the independently tested
[pybls21 library](https://github.com/jvitkauskas/pybls21).

The sensor, maintenance-button, and manual-fan-control designs adapt the work in
[@birdie1's PR #15](https://github.com/jvitkauskas/homeassistant_blauberg_s21/pull/15),
with attribution retained in this README and the commit co-author credit. The
implementation uses pybls21 5 snapshots and confirmed updates rather than
embedding a modified Modbus client in the integration.

The bundled icons and logos in `custom_components/blauberg_s21/brand/` are
unchanged copies of the integration's existing artwork from
[Home Assistant's brands repository](https://github.com/home-assistant/brands/tree/2406ed3b9dec262f2a17cde893227c523ebe2838/custom_integrations/blauberg_s21).
They are used to identify supported hardware. Product names and trademarks
belong to their respective owners; their use does not imply endorsement.
