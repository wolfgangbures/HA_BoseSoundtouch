"""Media player platform for Bose SoundTouch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import SoundTouchError, SoundTouchSource, SoundTouchState
from .const import DATA_MAC_LOOKUP, DATA_ZONE_CACHE, DOMAIN
from .coordinator import SoundTouchCoordinator

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.SELECT_SOURCE
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SoundTouchCoordinator = data["coordinator"]
    async_add_entities([SoundTouchMediaPlayer(coordinator, entry)], True)


class SoundTouchMediaPlayer(CoordinatorEntity[SoundTouchCoordinator], MediaPlayerEntity):
    """Representation of a Bose SoundTouch media player."""

    _attr_supported_features = SUPPORTED_FEATURES
    _attr_has_entity_name = False

    def __init__(self, coordinator: SoundTouchCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._sources: list[SoundTouchSource] | None = None
        self._attr_unique_id = entry.unique_id or (
            coordinator.data.device_id if coordinator.data else entry.entry_id
        )
        self._fallback_name = entry.title or "Bose SoundTouch"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        try:
            self._sources = await self.coordinator.client.async_get_sources()
        except SoundTouchError:
            self._sources = None
        self._ensure_mac_registered()
        self._cache_zone_members()

    def _handle_coordinator_update(self) -> None:
        self._ensure_mac_registered()
        self._cache_zone_members()
        super()._handle_coordinator_update()

    def _ensure_mac_registered(self) -> None:
        if not self.hass:
            return
        data = self.coordinator.data
        if not data or not data.device_id or not self.entity_id:
            return
        lookup = self.hass.data.setdefault(DOMAIN, {}).setdefault(DATA_MAC_LOOKUP, {})
        lookup[data.device_id.lower()] = self.entity_id

    def _mac_entity_lookup(self) -> dict[str, str]:
        if not self.hass:
            return {}
        lookup = self.hass.data.setdefault(DOMAIN, {}).setdefault(DATA_MAC_LOOKUP, {})
        data = self.coordinator.data
        if data and data.device_id and self.entity_id:
            lookup.setdefault(data.device_id.lower(), self.entity_id)
        return lookup

    def _zone_cache(self) -> dict[str, list[dict[str, str]]]:
        if not self.hass:
            return {}
        domain_data = self.hass.data.setdefault(DOMAIN, {})
        return domain_data.setdefault(DATA_ZONE_CACHE, {})

    def _cache_zone_members(self) -> None:
        if not self.hass:
            return
        data = self.coordinator.data
        if not data:
            return
        master_mac = (data.zone_master_mac or data.device_id or "").lower()
        if not master_mac:
            return
        members = [
            {"ip": member.ip, "mac": member.mac}
            for member in (data.zone_members or [])
            if member.mac
        ]
        if not members and data.device_id:
            members = [
                {
                    "ip": data.ip_address
                    or self.coordinator.client.control_ip,
                    "mac": data.device_id,
                }
            ]
        cache = self._zone_cache()
        cache[master_mac] = members

    def _get_zone_members(self) -> list[dict[str, str]]:
        data = self.coordinator.data
        members = [
            {"ip": member.ip, "mac": member.mac}
            for member in (data.zone_members or [])
            if member.mac
        ]
        if members:
            return members
        cache = self._zone_cache()
        master_mac = (data.zone_master_mac or data.device_id or "").lower()
        if master_mac and master_mac in cache:
            return cache[master_mac]
        if data and data.device_id:
            return [
                {
                    "ip": data.ip_address or self.coordinator.client.control_ip,
                    "mac": data.device_id,
                }
            ]
        return []

    def _map_zone_members_to_entities(
        self, members: list[dict[str, str]], lookup: dict[str, str]
    ) -> list[str]:
        seen: set[str] = set()
        entities: list[str] = []
        for member in members:
            mac = (member.get("mac") or "").lower()
            entity_id = lookup.get(mac)
            if entity_id and entity_id not in seen:
                seen.add(entity_id)
                entities.append(entity_id)
        return entities

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def name(self) -> str | None:
        base = self.coordinator.data.name if self.coordinator.data else self._fallback_name
        return f"Bose {base}".strip()

    @property
    def state(self) -> MediaPlayerState | None:
        state = self.coordinator.data.status if self.coordinator.data else None
        if not state:
            return None
        normalized = state.lower()
        if normalized.startswith("play"):
            return MediaPlayerState.PLAYING
        if "pause" in normalized:
            return MediaPlayerState.PAUSED
        if normalized in {"standby", "stop_state", "inactive"}:
            return MediaPlayerState.OFF
        if "buffer" in normalized:
            return MediaPlayerState.BUFFERING
        return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.volume / 100

    @property
    def is_volume_muted(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.is_muted

    @property
    def source(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        target = (data.source_account or data.source or "").lower()
        if self._sources and target:
            for item in self._sources:
                if item.matches(target):
                    return item.name
        return data.source_account or data.source

    @property
    def source_list(self) -> list[str] | None:
        if not self._sources:
            return None
        return [item.name for item in self._sources]

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if not data:
            return None
        raw_members = self._get_zone_members()
        members = [dict(member) for member in raw_members]
        attributes: dict[str, Any] = {
            "ip_address": data.ip_address,
            "mac_address": data.device_id,
            "zone_master": data.is_master,
            "zone_master_mac": data.zone_master_mac,
            "zone_members": members,
        }
        lookup = self._mac_entity_lookup()
        master_mac = (data.zone_master_mac or data.device_id or "").lower()
        master_entity = lookup.get(master_mac)
        group_entities = self._map_zone_members_to_entities(raw_members, lookup)
        if self.entity_id and self.entity_id not in group_entities:
            group_entities.append(self.entity_id)
        zone_master_entity = master_entity or (self.entity_id if data.is_master else None)
        zone_slaves = [entity_id for entity_id in group_entities if entity_id != zone_master_entity]
        if zone_master_entity or zone_slaves:
            attributes["soundtouch_zone"] = {
                "master": zone_master_entity or data.zone_master_mac,
                "is_master": data.is_master,
                "slaves": zone_slaves,
            }
        if group_entities:
            attributes["soundtouch_group"] = group_entities
        return attributes

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

    async def async_turn_on(self) -> None:
        await self._async_power_cycle()

    async def async_turn_off(self) -> None:
        await self._async_power_cycle()

    async def _async_power_cycle(self) -> None:
        await self.coordinator.client.async_press_key("POWER", "press")
        await self.coordinator.client.async_press_key("POWER", "release")
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        volume_value = max(0, min(100, round(volume * 100)))
        await self.coordinator.client.async_set_volume(volume_value)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        handled = False
        if self._sources:
            for item in self._sources:
                if item.name.lower() == source.lower():
                    await self.coordinator.client.async_select_source_item(item)
                    handled = True
                    break
        if not handled:
            await self.coordinator.client.async_select_source(source)
        await self.coordinator.async_request_refresh()
