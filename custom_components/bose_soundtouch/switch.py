"""Per-speaker volume fade switch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENABLE_VOLUME_FADE,
    CONF_PERSISTENT_VOLUME_OVERRIDE,
    DEFAULT_ENABLE_VOLUME_FADE,
    DEFAULT_PERSISTENT_VOLUME_OVERRIDE,
    DOMAIN,
)
from .coordinator import SoundTouchCoordinator
from .fade_settings import SoundTouchFadeSetting


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        SoundTouchVolumeFadeSwitch(coordinator, entry),
        SoundTouchPersistentVolumeOverrideSwitch(coordinator, entry),
    ])


class SoundTouchVolumeFadeSwitch(SoundTouchFadeSetting, SwitchEntity):
    """Enable fading for subsequent volume requests on this speaker."""

    _attr_name = "Volume fade"
    _attr_translation_key = "volume_fade"
    _attr_icon = "mdi:volume-source"
    _setting_key = CONF_ENABLE_VOLUME_FADE
    _default_value = DEFAULT_ENABLE_VOLUME_FADE

    def __init__(self, coordinator: SoundTouchCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, self._setting_key)

    @property
    def is_on(self) -> bool:
        return self._entry.options.get(self._setting_key, self._default_value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._set_setting(self._setting_key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._set_setting(self._setting_key, False)


class SoundTouchPersistentVolumeOverrideSwitch(SoundTouchVolumeFadeSwitch):
    """Choose whether to keep correcting errors and later volume disturbances."""

    _attr_name = "Persistent volume override"
    _attr_translation_key = "persistent_volume_override"
    _attr_icon = "mdi:volume-lock"
    _setting_key = CONF_PERSISTENT_VOLUME_OVERRIDE
    _default_value = DEFAULT_PERSISTENT_VOLUME_OVERRIDE
