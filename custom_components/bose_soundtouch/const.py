"""Constants for the Bose SoundTouch integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "bose_soundtouch"
PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]
DEFAULT_PORT = 8090
DEFAULT_POLL_INTERVAL = 15
DATA_MAC_LOOKUP = "mac_entity_lookup"
DATA_ZONE_CACHE = "zone_members_cache"
DATA_LAST_SOURCE = "last_source_cache"
