"""Time platform for Pool Filter top-up window."""
from __future__ import annotations

from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_TOP_UP_END, CONF_TOP_UP_START, DOMAIN
from .coordinator import PoolFilterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up time entities."""
    coordinator: PoolFilterCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            PoolFilterTopUpStartTime(coordinator),
            PoolFilterTopUpEndTime(coordinator),
        ]
    )


class PoolFilterTime(CoordinatorEntity, TimeEntity):
    """Base time entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PoolFilterCoordinator,
        key: str,
        name: str,
    ) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
        )

    @property
    def native_value(self) -> dt_time:
        """Return the current time."""
        value = self.coordinator.get_setting(self._key, "14:30")
        parts = value.split(":")
        return dt_time(int(parts[0]), int(parts[1]))

    async def async_set_value(self, value: dt_time) -> None:
        """Update the setting."""
        await self.coordinator.async_set_setting(self._key, value.strftime("%H:%M"))


class PoolFilterTopUpStartTime(PoolFilterTime):
    """Start of the top-up window."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, CONF_TOP_UP_START, "Top-up start")


class PoolFilterTopUpEndTime(PoolFilterTime):
    """End of the top-up window."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, CONF_TOP_UP_END, "Top-up end")
