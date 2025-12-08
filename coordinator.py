"""Update coordinator for Bose SoundTouch devices."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import SoundTouchClient, SoundTouchError, SoundTouchState
from .const import DEFAULT_POLL_INTERVAL


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

    async def _async_update_data(self) -> SoundTouchState:
        try:
            return await self.client.async_get_state()
        except SoundTouchError as err:
            raise UpdateFailed(err) from err
