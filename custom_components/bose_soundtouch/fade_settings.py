"""Shared device control state, persisted through Home Assistant config entries."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityCategory

from .const import (
    CONF_ENABLE_VOLUME_FADE,
    CONF_VOLUME_FADE_DURATION,
    DEFAULT_ENABLE_VOLUME_FADE,
    DEFAULT_VOLUME_FADE_DURATION,
    DOMAIN,
)
from .coordinator import SoundTouchCoordinator


class SoundTouchFadeSetting(Entity):
    """Local configuration control belonging to the existing speaker device."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: SoundTouchCoordinator, entry: ConfigEntry, suffix: str,
    ) -> None:
        super().__init__()
        self.coordinator = coordinator
        self._entry = entry
        base_unique = entry.unique_id or (
            coordinator.data.device_id if coordinator.data else entry.entry_id
        )
        self._attr_unique_id = f"{base_unique}_{suffix}"

    @property
    def device_info(self) -> dict[str, Any]:
        data = self.coordinator.data
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

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._entry.add_update_listener(self._async_entry_updated))

    async def _async_entry_updated(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.async_write_ha_state()

    def _set_setting(self, key: str, value: bool | int) -> None:
        options = {**self._entry.options, key: value}
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        # Apply synchronously so the next action in an automation sees the new value.
        self.coordinator.configure_volume(
            options.get(CONF_ENABLE_VOLUME_FADE, DEFAULT_ENABLE_VOLUME_FADE),
            options.get(CONF_VOLUME_FADE_DURATION, DEFAULT_VOLUME_FADE_DURATION),
        )
        self.async_write_ha_state()
