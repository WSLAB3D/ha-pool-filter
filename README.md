# Pool Filter

A Home Assistant custom integration for solar-aware pool filter control.

## Why a custom component instead of an add-on?

A Home Assistant **add-on** is a separate Docker container. A **custom component**
is Python code that runs inside Home Assistant. For this use case a custom
component is simpler, lighter and easier to deploy: just copy the folder into
`/config/custom_components`, restart HA, and add the integration. You do not need
Docker or a separate service.

## Goal

Run a pool filter for a configurable number of hours over a configurable
lookback window, preferring solar power, with a fixed top-up window that runs
the filter for any remaining deficit regardless of solar conditions.

## Default behaviour

- **Target**: 4 hours over a 2-day lookback.
- **Solar mode**: outside the top-up window, the filter runs when
  `PV >= house consumption + filter power + solar margin`, `grid import <= max grid import`
  and `battery % >= min battery %`.
- **Top-up window**: between the configured start and end times, if the
  accumulated runtime is still below the target, the filter runs for the
  remaining deficit.
- **Battery protection**: if a battery percentage sensor is configured, solar
  mode is only allowed when the battery is above the configured minimum.
- **Auto control**: a switch pauses or resumes the controller.
- **Runtime tracking**: total runtime, deficit, state, solar/battery conditions are
  exposed as sensors.
- **Adjustable settings**: target hours, lookback days, filter power, solar
  margin, max grid import, min battery % and the top-up window can all be changed
  from the UI.

## Entities

- `switch.pool_filter_auto_control` — enable/disable automatic control
- `sensor.pool_filter_runtime_lookback` — accumulated hours in the lookback window
- `sensor.pool_filter_deficit` — remaining hours needed to hit the target
- `sensor.pool_filter_state` — `on` / `off` / `paused`
- `sensor.pool_filter_solar_ok` — `yes` / `no`
- `sensor.pool_filter_battery_ok` — `yes` / `no`
- `number.pool_filter_target_hours`
- `number.pool_filter_lookback_days`
- `number.pool_filter_filter_power`
- `number.pool_filter_solar_margin`
- `number.pool_filter_max_grid_import`
- `number.pool_filter_min_battery_percentage`
- `time.pool_filter_top_up_start`
- `time.pool_filter_top_up_end`

## Installation with HACS (recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed.
2. In HACS, go to **Integrations > Custom repositories**.
3. Add `https://github.com/WSLAB3D/ha-pool-filter` with category **Integration**.
4. Install the **Pool Filter** integration.
5. Restart Home Assistant.
6. Add the integration via **Settings > Devices & Services > Add Integration**.
7. Select the pool filter switch, PV, house consumption, grid import, battery
   percentage sensor and configure the margins and top-up window.
8. You can reconfigure the selected entities later by going to
   **Settings > Devices & Services > Pool Filter > Configure**.

> The repository must be public or your HACS installation must have access to the
> private GitHub repository.

## Manual installation

1. Copy `custom_components/pool_filter` into your Home Assistant
   `/config/custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings > Devices & Services > Add Integration**.
4. Select the pool filter switch, PV, house consumption, grid import, battery
   percentage sensor and configure the margins and top-up window.
5. You can reconfigure the selected entities later by going to
   **Settings > Devices & Services > Pool Filter > Configure**.
