"""Update coordinator for Bose SoundTouch devices."""

from __future__ import annotations

import asyncio
from contextlib import suppress
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
from .const import (
    DEFAULT_ENABLE_VOLUME_FADE,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PERSISTENT_VOLUME_OVERRIDE,
    DEFAULT_VOLUME_FADE_DURATION,
    DEFAULT_VOLUME_FADE_OUT_DURATION,
    DESIRED_STATE_MAX_AGE,
    POLL_FAILURE_TOLERANCE,
    VOLUME_FADE_STEP_INTERVAL,
    VOLUME_RETRY_INTERVAL,
)
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
        self._volume_task: asyncio.Task[None] | None = None
        self._volume_lock = asyncio.Lock()
        self._volume_stopped = False
        self._enable_volume_fade = DEFAULT_ENABLE_VOLUME_FADE
        self._volume_fade_duration = DEFAULT_VOLUME_FADE_DURATION
        self._volume_fade_out_duration = DEFAULT_VOLUME_FADE_OUT_DURATION
        self._persistent_volume_override = DEFAULT_PERSISTENT_VOLUME_OVERRIDE
        self._desired_zone: list[SoundTouchZoneMember] | None = None
        self._desired_zone_at = 0.0

    @property
    def desired_volume(self) -> int | None:
        """Return the latest HA target, independent of reported speaker volume."""

        return self._desired_volume

    def configure_volume(
        self,
        enable_fade: bool,
        duration_ms: int,
        fade_out_duration_ms: int = DEFAULT_VOLUME_FADE_OUT_DURATION,
        persistent_override: bool = DEFAULT_PERSISTENT_VOLUME_OVERRIDE,
    ) -> None:
        """Update fade timing for new requests and the live correction policy."""

        self._enable_volume_fade = enable_fade
        self._volume_fade_duration = duration_ms
        self._volume_fade_out_duration = fade_out_duration_ms
        self._persistent_volume_override = persistent_override

    async def async_set_volume(self, volume: int) -> None:
        """Replace the target and start a single cancellable volume controller."""

        async with self._volume_lock:
            if self._volume_stopped:
                raise SoundTouchError("Volume controller has been unloaded")
            await self._async_cancel_volume_task()
            self._desired_volume = max(0, min(100, int(volume)))
            durations = (
                (self._volume_fade_duration / 1000, self._volume_fade_out_duration / 1000)
                if self._enable_volume_fade else (0.0, 0.0)
            )
            immediate = durations == (0.0, 0.0)
            failed = False
            if immediate:
                try:
                    await self.client.async_set_volume(self._desired_volume)
                except (asyncio.TimeoutError, ClientError, OSError, SoundTouchError) as err:
                    _LOGGER.warning(
                        "Could not set volume on %s to %s (persistent override=%s): %s",
                        self.client.host, self._desired_volume,
                        self._persistent_volume_override, err,
                    )
                    failed = True
            if not failed or self._persistent_volume_override:
                self._volume_task = self.hass.async_create_background_task(
                    self._async_drive_volume(self._desired_volume, durations),
                    f"SoundTouch volume ({self.client.host})",
                )
        if immediate:
            await self.async_request_refresh()

    async def _async_cancel_volume_task(self) -> None:
        if self._volume_task is not None:
            self._volume_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._volume_task
            self._volume_task = None

    async def async_stop_volume(self) -> None:
        """Stop pending writes before unloading this entry."""

        async with self._volume_lock:
            self._volume_stopped = True
            await self._async_cancel_volume_task()

    async def _async_drive_volume(
        self, target: int, durations: tuple[float, float],
    ) -> None:
        """Attempt the target; optionally retain it across errors and later drift."""

        retry_delay = VOLUME_RETRY_INTERVAL
        fade_pending = True
        while True:
            try:
                current = await self.client.async_get_volume()
                if current == target:
                    await self.async_request_refresh()
                    return
                duration = durations[0] if target > current else durations[1]
                if fade_pending and duration > 0:
                    # A failed fade resumes with target correction, not another full fade.
                    fade_pending = False
                    await self._async_fade_volume(current, target, duration)
                else:
                    fade_pending = False
                    await self.client.async_set_volume(target)
                retry_delay = VOLUME_RETRY_INTERVAL
            except (asyncio.TimeoutError, ClientError, OSError, SoundTouchError) as err:
                if not self._persistent_volume_override:
                    _LOGGER.warning(
                        "Volume request %s on %s stopped after an error; "
                        "persistent override is disabled: %s",
                        target, self.client.host, err,
                    )
                    return
                _LOGGER.warning(
                    "Volume target %s not confirmed on %s; retrying in %ss: %s",
                    target, self.client.host, retry_delay, err,
                )
                await asyncio.sleep(retry_delay)
                if not self._persistent_volume_override:
                    _LOGGER.info(
                        "Stopping pending volume retry on %s because persistent override was disabled",
                        self.client.host,
                    )
                    return
                retry_delay = min(retry_delay * 2, DEFAULT_POLL_INTERVAL)
                continue
            await asyncio.sleep(VOLUME_RETRY_INTERVAL)

    async def _async_fade_volume(self, start: int, target: int, duration: float) -> None:
        started = monotonic()
        deadline = started + duration
        last_sent = start
        while True:
            now = monotonic()
            progress = 1.0 if now >= deadline else (now - started) / duration
            volume = round(start + (target - start) * progress)
            if volume != last_sent:
                await self.client.async_set_volume(volume)
                last_sent = volume
            if progress >= 1:
                return
            await asyncio.sleep(min(VOLUME_FADE_STEP_INTERVAL, deadline - now))

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
        return await self._async_enforce_volume(state)

    async def _async_enforce_volume(self, state: SoundTouchState) -> SoundTouchState:
        """Correct drift on every successful poll, without fighting an active fade."""

        async with self._volume_lock:
            if (
                self._volume_stopped
                or not self._persistent_volume_override
                or self._desired_volume is None
                or state.volume == self._desired_volume
                or (self._volume_task is not None and not self._volume_task.done())
            ):
                return state
            _LOGGER.info(
                "Correcting volume on %s from %s to HA target %s",
                self.client.host, state.volume, self._desired_volume,
            )
            try:
                await self.client.async_set_volume(self._desired_volume)
                return await self.client.async_get_state()
            except (asyncio.TimeoutError, ClientError, OSError, SoundTouchError) as err:
                _LOGGER.warning("Could not correct volume on %s: %s", self.client.host, err)
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
        """Re-apply zone settings that may have been lost during the outage."""

        restored = False
        now = monotonic()

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
