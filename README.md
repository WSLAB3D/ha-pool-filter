# Pool Filter

A Home Assistant custom integration for solar-aware pool filter control.

## Goal

Run the pool filter for a configurable number of hours over a configurable
lookback window, preferring solar power, with a fixed top-up window that runs
the filter for any remaining deficit regardless of solar conditions.

## Default Behaviour

- **Target**: 4 hours over a 2-day lookback.
- **Solar mode**: outside the top-up window, the filter runs when
  `PV >= house consumption + filter power + solar margin` and `grid import <= max grid import`.
- **Top-up window**: between the configured start and end times, if the
  accumulated runtime is still below the target, the filter runs for the
  remaining deficit.
- **Auto control**: a switch enables or disables the controller.

## Configuration

Install by copying `custom_components/pool_filter` into your Home Assistant
`/config/custom_components` directory and restarting Home Assistant. Then add
the integration through **Settings > Devices & Services > Add Integration**.

The config flow asks for the pool filter switch, power sensors, margins, and
the top-up window.
