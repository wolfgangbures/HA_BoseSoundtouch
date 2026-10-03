"""Per-speaker volume fade switch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENABLE_VOLUME_FADE, DEFAULT_ENABLE_VOLUME_FADE, DOMAIN
from .coordinator import SoundTouchCoordinator
from .fade_settings import SoundTouchFadeSetting


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([SoundTouchVolumeFadeSwitch(coordinator, entry)])


class SoundTouchVolumeFadeSwitch(SoundTouchFadeSetting, SwitchEntity):
    """Enable fading for subsequent volume requests on this speaker."""

    _attr_name = "Volume fade"
    _attr_translation_key = "volume_fade"
    _attr_icon = "mdi:volume-source"

    def __init__(self, coordinator: SoundTouchCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, CONF_ENABLE_VOLUME_FADE)

    @property
    def is_on(self) -> bool:
        return self._entry.options.get(CONF_ENABLE_VOLUME_FADE, DEFAULT_ENABLE_VOLUME_FADE)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._set_setting(CONF_ENABLE_VOLUME_FADE, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._set_setting(CONF_ENABLE_VOLUME_FADE, False)
