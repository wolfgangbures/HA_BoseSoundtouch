"""Config flow for the Bose SoundTouch integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import SoundTouchClient, SoundTouchError
from .const import DOMAIN


async def _async_validate_input(hass: HomeAssistant, host: str) -> dict[str, str]:
    session = async_get_clientsession(hass)
    client = SoundTouchClient(session, host)
    return await client.async_identify()


class BoseSoundTouchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input["host"].strip()
            try:
                info = await _async_validate_input(self.hass, host)
            except SoundTouchError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info["device_id"])
                self._abort_if_unique_id_configured()
                title = info.get("name") or host
                return self.async_create_entry(
                    title=title,
                    data={"host": host},
                )

        data_schema = vol.Schema(
            {vol.Required("host"): str}
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
