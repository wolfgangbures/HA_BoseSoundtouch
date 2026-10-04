"""Per-speaker volume fade duration control."""

from __future__ import annotations

import math

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_VOLUME_FADE_DURATION,
    CONF_VOLUME_FADE_OUT_DURATION,
    DEFAULT_VOLUME_FADE_DURATION,
    DEFAULT_VOLUME_FADE_OUT_DURATION,
    DOMAIN,
    MAX_VOLUME_FADE_DURATION,
)
from .coordinator import SoundTouchCoordinator
from .fade_settings import SoundTouchFadeSetting


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        SoundTouchVolumeFadeDurationNumber(coordinator, entry),
        SoundTouchVolumeFadeOutDurationNumber(coordinator, entry),
    ])


class SoundTouchVolumeFadeDurationNumber(SoundTouchFadeSetting, NumberEntity):
    """Set fade-in duration, preserving the original entity ID and saved value."""

    _attr_name = "Volume fade-in duration"
    _attr_translation_key = "volume_fade_duration"
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "ms"
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_VOLUME_FADE_DURATION
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _setting_key = CONF_VOLUME_FADE_DURATION
    _default_value = DEFAULT_VOLUME_FADE_DURATION

    def __init__(self, coordinator: SoundTouchCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, self._setting_key)

    @property
    def native_value(self) -> int:
        return self._entry.options.get(self._setting_key, self._default_value)

    async def async_set_native_value(self, value: float) -> None:
        if (
            not math.isfinite(value)
            or not 0 <= value <= MAX_VOLUME_FADE_DURATION
            or value != int(value)
        ):
            raise HomeAssistantError("Volume fade duration must be an integer from 0 to 60000 ms")
        self._set_setting(self._setting_key, int(value))


class SoundTouchVolumeFadeOutDurationNumber(SoundTouchVolumeFadeDurationNumber):
    """Set a separate duration for decreases in volume."""

    _attr_name = "Volume fade-out duration"
    _attr_translation_key = "volume_fade_out_duration"
    _setting_key = CONF_VOLUME_FADE_OUT_DURATION
    _default_value = DEFAULT_VOLUME_FADE_OUT_DURATION
