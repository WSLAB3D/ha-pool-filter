"""Data update coordinator for Pool Filter."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FILTER_POWER,
    CONF_FILTER_SWITCH,
    CONF_GRID_IMPORT,
    CONF_HOUSE_CONSUMPTION,
    CONF_LOOKBACK_DAYS,
    CONF_MAX_GRID_IMPORT,
    CONF_PV_POWER,
    CONF_SOLAR_MARGIN,
    CONF_TARGET_HOURS,
    CONF_TOP_UP_END,
    CONF_TOP_UP_START,
    DOMAIN,
)

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)
_LOGGER = logging.getLogger(__name__)


def _safe_float(state, default: float = 0.0) -> float:
    """Return a float state value or a default."""
    if state is None or state.state in ("unknown", "unavailable", "none", ""):
        return default
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return default


def _parse_time(value: str) -> time:
    """Parse a HH:MM string into a time object."""
    parts = value.split(":")
    return time(int(parts[0]), int(parts[1]))


def _in_time_window(now: datetime, start: time, end: time) -> bool:
    """Return True if now falls between start and end (handles wrap around midnight)."""
    start_dt = now.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
    end_dt = now.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return start_dt <= now < end_dt


class PoolFilterCoordinator(DataUpdateCoordinator):
    """Coordinator for pool filter control."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self._store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._store_data: dict[str, Any] = {}
        self._settings: dict[str, Any] = {}
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
            config_entry=entry,
        )

    @property
    def auto_control(self) -> bool:
        """Return whether automatic control is enabled."""
        return self._settings.get("auto_control", True)

    async def async_set_auto_control(self, value: bool) -> None:
        """Set auto control state."""
        self._settings["auto_control"] = value
        await self._async_save_settings()
        await self.async_request_refresh()

    async def async_set_setting(self, key: str, value: Any) -> None:
        """Update a runtime setting."""
        self._settings[key] = value
        await self._async_save_settings()
        await self.async_request_refresh()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Return a setting, falling back to config entry data."""
        return self._settings.get(key, self.entry.data.get(key, default))

    async def _async_setup(self) -> None:
        """Load stored runtime and settings."""
        stored = await self._store.async_load()
        if stored is None:
            stored = {
                "events": [],
                "last_state": "unknown",
                "last_state_time": None,
                "settings": {},
            }
        self._store_data = stored

        settings = dict(stored.get("settings", {}))
        defaults = {
            "auto_control": True,
            CONF_FILTER_POWER: self.entry.data.get(CONF_FILTER_POWER, 1150),
            CONF_SOLAR_MARGIN: self.entry.data.get(CONF_SOLAR_MARGIN, 300),
            CONF_MAX_GRID_IMPORT: self.entry.data.get(CONF_MAX_GRID_IMPORT, 100),
            CONF_TARGET_HOURS: self.entry.data.get(CONF_TARGET_HOURS, 4),
            CONF_LOOKBACK_DAYS: self.entry.data.get(CONF_LOOKBACK_DAYS, 2),
            CONF_TOP_UP_START: self.entry.data.get(CONF_TOP_UP_START, "14:30"),
            CONF_TOP_UP_END: self.entry.data.get(CONF_TOP_UP_END, "16:30"),
        }
        for key, value in defaults.items():
            if key not in settings:
                settings[key] = value
        self._settings = settings
        self._store_data["settings"] = self._settings
        await self._store.async_save(self._store_data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update runtime and decide filter state."""
        if not self._store_data:
            await self._async_setup()
        if not self._store_data:
            _LOGGER.error("Failed to initialize Pool Filter store")
            return {}

        now = dt_util.utcnow()
        now_local = dt_util.as_local(now)

        filter_entity = self.entry.data[CONF_FILTER_SWITCH]
        state_obj = self.hass.states.get(filter_entity)
        current_state = state_obj.state if state_obj else "unknown"
        if current_state not in ("on", "off"):
            current_state = "unknown"

        last_state = self._store_data.get("last_state", "unknown")
        last_state_time_str = self._store_data.get("last_state_time")
        last_state_time = (
            dt_util.parse_datetime(last_state_time_str)
            if last_state_time_str
            else None
        )

        events: list[dict[str, str]] = list(self._store_data.get("events", []))

        if last_state == "on" and last_state_time and last_state_time < now:
            # checkpoint running on-time up to now
            events.append({"start": last_state_time.isoformat(), "end": now.isoformat()})
            if current_state == "on":
                last_state_time = now
            else:
                last_state_time = None

        if current_state in ("on", "off"):
            self._store_data["last_state"] = current_state
            self._store_data["last_state_time"] = (
                now.isoformat() if current_state == "on" else None
            )
        else:
            self._store_data["last_state"] = last_state if last_state in ("on", "off") else "off"
            self._store_data["last_state_time"] = (
                last_state_time.isoformat() if last_state_time and last_state_time < now else None
            )

        lookback_days = self.get_setting(CONF_LOOKBACK_DAYS, 2)
        cutoff = now - timedelta(days=lookback_days)
        kept_events = []
        for event in events:
            end = dt_util.parse_datetime(event.get("end"))
            if end and end > cutoff:
                kept_events.append(event)
        self._store_data["events"] = kept_events

        runtime = timedelta()
        for event in kept_events:
            start = dt_util.parse_datetime(event.get("start"))
            end = dt_util.parse_datetime(event.get("end"))
            if not start or not end:
                continue
            if start < cutoff:
                start = cutoff
            if end > now:
                end = now
            if end > start:
                runtime += end - start

        runtime_seconds = runtime.total_seconds()
        target_seconds = self.get_setting(CONF_TARGET_HOURS, 4) * 3600
        deficit = max(0.0, target_seconds - runtime_seconds)

        top_up_start = _parse_time(self.get_setting(CONF_TOP_UP_START, "14:30"))
        top_up_end = _parse_time(self.get_setting(CONF_TOP_UP_END, "16:30"))
        in_top_up = _in_time_window(now_local, top_up_start, top_up_end)

        pv_state = self.hass.states.get(self.entry.data[CONF_PV_POWER])
        house_state = self.hass.states.get(self.entry.data[CONF_HOUSE_CONSUMPTION])
        grid_import = 0.0
        grid_entity = self.entry.data.get(CONF_GRID_IMPORT)
        if grid_entity:
            grid_import = _safe_float(self.hass.states.get(grid_entity), 0.0)

        pv = _safe_float(pv_state, 0.0)
        house = _safe_float(house_state, 0.0)

        filter_power = self.get_setting(CONF_FILTER_POWER, 1150)
        solar_margin = self.get_setting(CONF_SOLAR_MARGIN, 300)
        max_grid_import = self.get_setting(CONF_MAX_GRID_IMPORT, 100)

        solar_ok = (
            pv >= house + filter_power + solar_margin
            and grid_import <= max_grid_import
        )

        desired_state: str | None = None
        if not self.auto_control:
            desired_state = None
        elif in_top_up and deficit > 0:
            desired_state = "on"
        elif runtime_seconds >= target_seconds:
            desired_state = "off"
        elif solar_ok:
            desired_state = "on"
        else:
            desired_state = "off"

        if (
            desired_state in ("on", "off")
            and desired_state != current_state
            and current_state in ("on", "off")
        ):
            try:
                await self.hass.services.async_call(
                    "switch",
                    "turn_on" if desired_state == "on" else "turn_off",
                    {"entity_id": filter_entity},
                    blocking=True,
                )
            except Exception as exc:
                _LOGGER.error("Failed to set filter switch %s: %s", filter_entity, exc)

        self._store_data["settings"] = self._settings
        await self._store.async_save(self._store_data)

        return {
            "runtime_seconds": runtime_seconds,
            "deficit_seconds": deficit,
            "desired_state": desired_state,
            "current_state": current_state,
            "in_top_up": in_top_up,
            "solar_ok": solar_ok,
            "auto_control": self.auto_control,
            "settings": self._settings,
            "events_count": len(kept_events),
        }

    async def _async_save_settings(self) -> None:
        """Persist settings."""
        self._store_data["settings"] = self._settings
        await self._store.async_save(self._store_data)
