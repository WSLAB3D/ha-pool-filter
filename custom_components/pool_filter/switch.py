"""Switch platform for Pool Filter."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up switch entities."""
    coordinator: PoolFilterCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([PoolFilterAutoControlSwitch(coordinator)])


class PoolFilterAutoControlSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to pause/resume automatic pool filter control."""

    _attr_has_entity_name = True
    _attr_name = "Auto control"

    def __init__(self, coordinator: PoolFilterCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_auto_control"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
        )

    @property
    def is_on(self) -> bool:
        """Return True if auto control is enabled."""
        return self.coordinator.auto_control

    async def async_turn_on(self, **kwargs) -> None:
        """Enable auto control."""
        await self.coordinator.async_set_auto_control(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable auto control."""
        await self.coordinator.async_set_auto_control(False)
        self.async_write_ha_state()
