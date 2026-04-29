"""Switch platform for Sentry3D."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Sentry3DCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Sentry3D switch entities."""
    coordinator: Sentry3DCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Sentry3DMonitoringSwitch(coordinator, entry)])


class Sentry3DMonitoringSwitch(CoordinatorEntity[Sentry3DCoordinator], SwitchEntity):
    """Switch entity to enable or disable monitoring."""

    _attr_has_entity_name = True
    _attr_name = "Monitoring"
    _attr_icon = "mdi:cctv"

    def __init__(self, coordinator: Sentry3DCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_monitoring"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": coordinator.integration_name,
            "manufacturer": "Sentry3D",
            "model": "RTSP + Ollama Vision Monitor",
        }

    @property
    def is_on(self) -> bool:
        """Return true when monitoring is enabled."""
        return self.coordinator.monitoring_enabled

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable monitoring."""
        await self.coordinator.async_set_monitoring_enabled(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable monitoring."""
        await self.coordinator.async_set_monitoring_enabled(False)
