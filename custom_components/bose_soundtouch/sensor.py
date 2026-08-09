"""Sensor platform for Bose SoundTouch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import SoundTouchState
from .const import DOMAIN
from .coordinator import SoundTouchCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SoundTouch sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SoundTouchCoordinator = data["coordinator"]
    async_add_entities(
        [
            SoundTouchVolumeSensor(coordinator, entry),
            SoundTouchZoneSensor(coordinator, entry),
            SoundTouchInputSensor(coordinator, entry),
        ]
    )


class SoundTouchBaseSensor(CoordinatorEntity[SoundTouchCoordinator], SensorEntity):
    """Base class for SoundTouch coordinator-backed sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SoundTouchCoordinator, entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        base_unique = entry.unique_id or (
            coordinator.data.device_id if coordinator.data else entry.entry_id
        )
        self._attr_unique_id = f"{base_unique}_{suffix}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def device_info(self) -> dict[str, Any]:
        data: SoundTouchState | None = self.coordinator.data
        if not data:
            return {
                "identifiers": {(DOMAIN, self._entry.entry_id)},
                "manufacturer": "Bose",
            }
        return {
            "identifiers": {(DOMAIN, data.device_id)},
            "manufacturer": "Bose",
            "name": data.name,
            "model": data.device_type,
        }


class SoundTouchVolumeSensor(SoundTouchBaseSensor):
    """Expose current volume as a dedicated sensor."""

    _attr_name = "Volume"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:volume-high"

    def __init__(self, coordinator: SoundTouchCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "volume")

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.volume


class SoundTouchZoneSensor(SoundTouchBaseSensor):
    """Expose zone membership/master details as a sensor value."""

    _attr_name = "Zone"
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, coordinator: SoundTouchCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "zone")

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        if len(data.zone_members or []) <= 1:
            return "standalone"
        return data.zone_master_mac or data.device_id

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if not data:
            return None
        return {
            "is_master": data.is_master,
            "zone_master_mac": data.zone_master_mac,
            "zone_size": len(data.zone_members or []),
        }


class SoundTouchInputSensor(SoundTouchBaseSensor):
    """Expose current source/input as a dedicated sensor."""

    _attr_name = "Input"
    _attr_icon = "mdi:audio-input-stereo-minijack"

    def __init__(self, coordinator: SoundTouchCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "input")

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.source_account or data.source