"""Data update coordinator for Pool Filter."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BATTERY_PERCENTAGE,
    CONF_COUNTDOWN_ENTITY,
    CONF_FILTER_POWER,
    CONF_FILTER_SWITCH,
    CONF_GRID_IMPORT,
    CONF_HOUSE_CONSUMPTION,
    CONF_LOOKBACK_DAYS,
    CONF_MAX_GRID_IMPORT,
    CONF_MIN_BATTERY_PERCENTAGE,
    CONF_NOTIFY_SERVICE,
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
        self._unsub_state_change: Callable[[], None] | None = None

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

        # Persist configuration keys through the config entry so changes survive
        # restarts and updates made in the OptionsFlow are reflected immediately.
        if key != "auto_control":
            new_data = dict(self.entry.data)
            new_data[key] = value
            self.hass.config_entries.async_update_entry(self.entry, data=new_data)

        await self._async_save_settings()
        await self.async_request_refresh()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Return a setting, falling back to config entry data."""
        return self._settings.get(key, self.entry.data.get(key, default))

    async def async_setup(self) -> None:
        """Load storage and start listeners."""
        await self._async_setup()

        filter_entity = self.entry.data[CONF_FILTER_SWITCH]

        @callback
        def _state_change(event: Event) -> None:
            """Notify if the filter switch goes unavailable/unknown while on."""
            if not self.entry.data.get(CONF_NOTIFY_SERVICE):
                return
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            if (
                old_state is not None
                and old_state.state == "on"
                and new_state is not None
                and new_state.state in ("unavailable", "unknown")
            ):
                self.hass.async_create_task(
                    self._async_send_notification(
                        "Pool Filter Plug Offline",
                        f"Pool Filter plug ({filter_entity}) is now {new_state.state} "
                        "and was last on. Please check it is not stuck running.",
                    )
                )

        self._unsub_state_change = async_track_state_change_event(
            self.hass, filter_entity, _state_change
        )

    async def async_unload(self) -> None:
        """Cancel listeners."""
        if self._unsub_state_change is not None:
            self._unsub_state_change()
            self._unsub_state_change = None

    async def _async_send_notification(self, title: str, message: str) -> None:
        """Send a notification to the configured service."""
        service = self.entry.data.get(CONF_NOTIFY_SERVICE, "")
        if not service or "." not in service:
            return
        domain, service_name = service.split(".", 1)
        try:
            await self.hass.services.async_call(
                domain,
                service_name,
                {"title": title, "message": message},
                blocking=False,
            )
        except Exception as exc:
            _LOGGER.error("Failed to send notification: %s", exc)

    async def _async_set_countdown(self, seconds: int) -> None:
        """Set the switch's fallback countdown timer, if configured.

        If the configured timer entity is unavailable or missing, this is a
        no-op so the integration still works for switches without a timer.
        """
        countdown_entity = self.entry.data.get(CONF_COUNTDOWN_ENTITY)
        if not countdown_entity:
            return

        state = self.hass.states.get(countdown_entity)
        if state is None or state.state in ("unknown", "unavailable", "none"):
            return

        # Clamp to the number entity's max so the service call does not fail.
        max_value = state.attributes.get("max")
        value = max(seconds, 0)
        if max_value is not None:
            try:
                value = min(value, float(max_value))
            except (ValueError, TypeError):
                pass

        try:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": countdown_entity, "value": value},
                blocking=False,
            )
        except Exception as exc:
            _LOGGER.error("Failed to set countdown %s: %s", countdown_entity, exc)

    async def _async_setup(self) -> None:
        """Load stored runtime and auto-control state."""
        stored = await self._store.async_load()
        if stored is None:
            stored = {
                "events": [],
                "last_state": "unknown",
                "last_state_time": None,
                "settings": {},
            }
        self._store_data = stored

        # Only auto_control is kept in local storage. Config values (target
        # hours, margins, top-up window, etc.) live in entry.data so the
        # OptionsFlow and dashboard numbers always stay in sync.
        self._settings = {
            "auto_control": stored.get("settings", {}).get("auto_control", True)
        }
        await self._async_save_settings()

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

        battery_percentage = 100.0
        battery_entity = self.entry.data.get(CONF_BATTERY_PERCENTAGE)
        if battery_entity:
            battery_percentage = _safe_float(
                self.hass.states.get(battery_entity), 100.0
            )

        pv = _safe_float(pv_state, 0.0)
        house = _safe_float(house_state, 0.0)

        filter_power = self.get_setting(CONF_FILTER_POWER, 1150)
        solar_margin = self.get_setting(CONF_SOLAR_MARGIN, 300)
        max_grid_import = self.get_setting(CONF_MAX_GRID_IMPORT, 100)
        min_battery_percentage = self.get_setting(CONF_MIN_BATTERY_PERCENTAGE, 20)

        battery_ok = battery_percentage >= min_battery_percentage

        solar_ok = (
            pv >= house + filter_power + solar_margin
            and grid_import <= max_grid_import
            and battery_ok
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
                if desired_state == "on":
                    await self._async_set_countdown(int(deficit))
                else:
                    await self._async_set_countdown(0)
            except Exception as exc:
                _LOGGER.error("Failed to set filter switch %s: %s", filter_entity, exc)
        elif desired_state == "on" and current_state == "on":
            # Keep the switch's own fallback timer in sync with remaining runtime
            await self._async_set_countdown(int(deficit))

        await self._async_save_settings()

        return {
            "runtime_seconds": runtime_seconds,
            "deficit_seconds": deficit,
            "desired_state": desired_state,
            "current_state": current_state,
            "in_top_up": in_top_up,
            "solar_ok": solar_ok,
            "battery_ok": battery_ok,
            "auto_control": self.auto_control,
            "settings": self._settings,
            "events_count": len(kept_events),
        }

    async def _async_save_settings(self) -> None:
        """Persist runtime events and auto-control flag."""
        self._store_data["settings"] = {
            "auto_control": self._settings.get("auto_control", True)
        }
        await self._store.async_save(self._store_data)
