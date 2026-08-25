"""Update coordinator for Bose SoundTouch devices."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from time import monotonic

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import (
    SoundTouchClient,
    SoundTouchError,
    SoundTouchState,
    SoundTouchZoneMember,
)
from .const import DEFAULT_POLL_INTERVAL, DESIRED_STATE_MAX_AGE, POLL_FAILURE_TOLERANCE
from .utils import same_zone_members


_LOGGER = logging.getLogger(__name__)


class SoundTouchCoordinator(DataUpdateCoordinator[SoundTouchState]):
    """Central place that keeps the latest SoundTouch state."""

    def __init__(self, hass: HomeAssistant, client: SoundTouchClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Bose SoundTouch ({client.host})",
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )
        self.client = client
        self._failure_count = 0
        self._desired_volume: int | None = None
        self._desired_volume_at = 0.0
        self._desired_zone: list[SoundTouchZoneMember] | None = None
        self._desired_zone_at = 0.0

    def remember_desired_volume(self, volume: int) -> None:
        """Remember the requested volume so it can be restored after an outage."""

        self._desired_volume = max(0, min(100, int(volume)))
        self._desired_volume_at = monotonic()

    def remember_desired_zone(self, members: list[SoundTouchZoneMember]) -> None:
        """Remember the zone topology this speaker should be mastering."""

        self._desired_zone = list(members)
        self._desired_zone_at = monotonic()

    async def _async_update_data(self) -> SoundTouchState:
        try:
            state = await self.client.async_get_state()
        except (asyncio.TimeoutError, ClientError, OSError) as err:
            return self._handle_poll_failure(
                f"Transport error while polling {self.client.host}: {err}", err
            )
        except SoundTouchError as err:
            return self._handle_poll_failure(str(err), err)

        recovered = self._failure_count > 0
        self._failure_count = 0
        if recovered:
            _LOGGER.info("Recovered communication with %s", self.client.host)
            state = await self._async_restore_desired_state(state)
        return state

    def _handle_poll_failure(self, message: str, err: Exception) -> SoundTouchState:
        """Keep the last known state for a few failed polls before going unavailable."""

        self._failure_count += 1
        if self.data is not None and self._failure_count <= POLL_FAILURE_TOLERANCE:
            _LOGGER.warning(
                "%s (failure %s/%s, keeping last known state)",
                message,
                self._failure_count,
                POLL_FAILURE_TOLERANCE,
            )
            return self.data
        raise UpdateFailed(message) from err

    async def _async_restore_desired_state(self, state: SoundTouchState) -> SoundTouchState:
        """Re-apply volume and zone settings that may have been lost during the outage."""

        restored = False
        now = monotonic()

        if (
            self._desired_volume is not None
            and now - self._desired_volume_at <= DESIRED_STATE_MAX_AGE
            and state.volume != self._desired_volume
        ):
            _LOGGER.info(
                "Restoring volume %s on %s after recovery (device reported %s)",
                self._desired_volume,
                self.client.host,
                state.volume,
            )
            try:
                await self.client.async_set_volume(self._desired_volume)
                restored = True
            except SoundTouchError as err:
                _LOGGER.warning("Could not restore volume on %s: %s", self.client.host, err)

        if self._desired_zone is not None and now - self._desired_zone_at <= DESIRED_STATE_MAX_AGE:
            current = [
                member
                for member in state.zone_members or []
                if (member.mac or "").lower() != (state.device_id or "").lower()
            ]
            if not same_zone_members(current, self._desired_zone):
                _LOGGER.info("Restoring zone membership on %s after recovery", self.client.host)
                try:
                    await self.client.async_set_zone(self._desired_zone)
                    restored = True
                except SoundTouchError as err:
                    _LOGGER.warning("Could not restore zone on %s: %s", self.client.host, err)
            self._desired_zone = None

        if not restored:
            return state
        try:
            return await self.client.async_get_state()
        except (asyncio.TimeoutError, ClientError, OSError, SoundTouchError) as err:
            _LOGGER.debug("Re-read after restore failed on %s: %s", self.client.host, err)
            return state
