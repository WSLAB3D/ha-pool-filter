# Pool Filter

A Home Assistant custom integration for solar-aware pool filter control.

## Goal

Run a pool filter for a configurable number of hours over a configurable
lookback window, preferring solar power, with a fixed top-up window that runs
the filter for any remaining deficit regardless of solar conditions.

## Default behaviour

- **Target**: 4 hours over a 2-day lookback.
- **Solar mode**: outside the top-up window, the filter runs when
  `PV >= house consumption + filter power + solar margin` and `grid import <= max grid import`.
- **Top-up window**: between the configured start and end times, if the
  accumulated runtime is still below the target, the filter runs for the
  remaining deficit.
- **Auto control**: a switch pauses or resumes the controller.
- **Runtime tracking**: total runtime, deficit, state and solar conditions are
  exposed as sensors.
- **Adjustable settings**: target hours, lookback days, filter power, solar
  margin, max grid import and the top-up window can all be changed from the UI.

## Entities

- `switch.pool_filter_auto_control` — enable/disable automatic control
- `sensor.pool_filter_runtime_lookback` — accumulated hours in the lookback window
- `sensor.pool_filter_deficit` — remaining hours needed to hit the target
- `sensor.pool_filter_state` — `on` / `off` / `paused`
- `sensor.pool_filter_solar_ok` — `yes` / `no`
- `number.pool_filter_target_hours`
- `number.pool_filter_lookback_days`
- `number.pool_filter_filter_power`
- `number.pool_filter_solar_margin`
- `number.pool_filter_max_grid_import`
- `time.pool_filter_top_up_start`
- `time.pool_filter_top_up_end`

## Installation

1. Copy `custom_components/pool_filter` into your Home Assistant
   `/config/custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings > Devices & Services > Add Integration**.
4. Select the pool filter switch, power sensors, and configure the default
   margins and top-up window.
