"""Constants for the Bose SoundTouch integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "bose_soundtouch"
PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SENSOR]
DEFAULT_PORT = 8090
DEFAULT_POLL_INTERVAL = 15
# Number of consecutive poll failures tolerated before the entity goes unavailable.
POLL_FAILURE_TOLERANCE = 3
# Desired zone values older than this (seconds) are not re-applied after a recovery.
DESIRED_STATE_MAX_AGE = 600
CONF_ENABLE_VOLUME_FADE = "enable_volume_fade"
CONF_VOLUME_FADE_DURATION = "volume_fade_duration"
DEFAULT_ENABLE_VOLUME_FADE = False
DEFAULT_VOLUME_FADE_DURATION = 1000
VOLUME_FADE_STEP_INTERVAL = 0.1
VOLUME_RETRY_INTERVAL = 1
DATA_MAC_LOOKUP = "mac_entity_lookup"
DATA_ZONE_CACHE = "zone_members_cache"
DATA_LAST_SOURCE = "last_source_cache"
