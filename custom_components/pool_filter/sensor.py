"""Sensor platform for Pool Filter."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PoolFilterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: PoolFilterCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            PoolFilterRuntimeSensor(coordinator),
            PoolFilterDeficitSensor(coordinator),
            PoolFilterStateSensor(coordinator),
            PoolFilterSolarOkSensor(coordinator),
        ]
    )


class PoolFilterSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Pool Filter."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PoolFilterCoordinator, key: str, name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
        )


class PoolFilterRuntimeSensor(PoolFilterSensor):
    """Runtime accumulated over the lookback window."""

    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 2
    _attr_state_class = "measurement"

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "runtime_lookback", "Runtime lookback")

    @property
    def native_value(self) -> float:
        """Return runtime in hours."""
        return round(self.coordinator.data.get("runtime_seconds", 0) / 3600, 2)


class PoolFilterDeficitSensor(PoolFilterSensor):
    """Remaining runtime needed to hit the target."""

    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 2
    _attr_state_class = "measurement"

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "deficit", "Deficit")

    @property
    def native_value(self) -> float:
        """Return deficit in hours."""
        return round(self.coordinator.data.get("deficit_seconds", 0) / 3600, 2)


class PoolFilterStateSensor(PoolFilterSensor):
    """Current control state."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "state", "State")

    @property
    def native_value(self) -> str:
        """Return desired state, or paused if auto control is off."""
        desired = self.coordinator.data.get("desired_state")
        if desired is None:
            return "paused"
        return desired


class PoolFilterSolarOkSensor(PoolFilterSensor):
    """Whether solar conditions are sufficient to run the filter."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "solar_ok", "Solar OK")

    @property
    def native_value(self) -> str:
        """Return yes/no."""
        return "yes" if self.coordinator.data.get("solar_ok") else "no"
