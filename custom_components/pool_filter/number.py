"""Number platform for Pool Filter settings."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_FILTER_POWER,
    CONF_LOOKBACK_DAYS,
    CONF_MAX_GRID_IMPORT,
    CONF_MIN_BATTERY_PERCENTAGE,
    CONF_SOLAR_MARGIN,
    CONF_TARGET_HOURS,
    DOMAIN,
)
from .coordinator import PoolFilterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator: PoolFilterCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            PoolFilterTargetHoursNumber(coordinator),
            PoolFilterLookbackDaysNumber(coordinator),
            PoolFilterFilterPowerNumber(coordinator),
            PoolFilterSolarMarginNumber(coordinator),
            PoolFilterMaxGridImportNumber(coordinator),
            PoolFilterMinBatteryPercentageNumber(coordinator),
        ]
    )


class PoolFilterNumber(CoordinatorEntity, NumberEntity):
    """Base number entity."""

    _attr_has_entity_name = True
    _attr_mode = "auto"

    def __init__(
        self,
        coordinator: PoolFilterCoordinator,
        key: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None = None,
        device_class: NumberDeviceClass | None = None,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
        )

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.get_setting(self._key)

    async def async_set_native_value(self, value: float) -> None:
        """Update the setting."""
        await self.coordinator.async_set_setting(self._key, value)


class PoolFilterTargetHoursNumber(PoolFilterNumber):
    """Daily target hours."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            CONF_TARGET_HOURS,
            "Target hours",
            0,
            24,
            0.5,
            UnitOfTime.HOURS,
            NumberDeviceClass.DURATION,
        )


class PoolFilterLookbackDaysNumber(PoolFilterNumber):
    """Lookback window in days."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            CONF_LOOKBACK_DAYS,
            "Lookback days",
            1,
            7,
            1,
            "days",
        )


class PoolFilterFilterPowerNumber(PoolFilterNumber):
    """Estimated filter power draw."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            CONF_FILTER_POWER,
            "Filter power",
            0,
            10000,
            50,
            UnitOfPower.WATT,
            NumberDeviceClass.POWER,
        )


class PoolFilterSolarMarginNumber(PoolFilterNumber):
    """Required solar surplus above filter power."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            CONF_SOLAR_MARGIN,
            "Solar margin",
            0,
            5000,
            50,
            UnitOfPower.WATT,
            NumberDeviceClass.POWER,
        )


class PoolFilterMaxGridImportNumber(PoolFilterNumber):
    """Maximum grid import allowed while running on solar."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            CONF_MAX_GRID_IMPORT,
            "Max grid import",
            0,
            10000,
            50,
            UnitOfPower.WATT,
            NumberDeviceClass.POWER,
        )


class PoolFilterMinBatteryPercentageNumber(PoolFilterNumber):
    """Minimum battery percentage required for solar mode."""

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            CONF_MIN_BATTERY_PERCENTAGE,
            "Min battery percentage",
            0,
            100,
            1,
            PERCENTAGE,
        )
