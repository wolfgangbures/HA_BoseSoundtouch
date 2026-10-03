"""Config flow for the Bose SoundTouch integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import SoundTouchClient, SoundTouchError
from .const import (
    CONF_ENABLE_VOLUME_FADE,
    CONF_VOLUME_FADE_DURATION,
    DEFAULT_ENABLE_VOLUME_FADE,
    DEFAULT_VOLUME_FADE_DURATION,
    DOMAIN,
)


def _volume_schema(options: dict) -> dict:
    return {
        vol.Optional(
            CONF_ENABLE_VOLUME_FADE,
            default=options.get(CONF_ENABLE_VOLUME_FADE, DEFAULT_ENABLE_VOLUME_FADE),
        ): bool,
        vol.Optional(
            CONF_VOLUME_FADE_DURATION,
            default=options.get(CONF_VOLUME_FADE_DURATION, DEFAULT_VOLUME_FADE_DURATION),
        ): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }


async def _async_validate_input(hass: HomeAssistant, host: str) -> dict[str, str]:
    session = async_get_clientsession(hass)
    client = SoundTouchClient(session, host)
    return await client.async_identify()


class BoseSoundTouchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BoseSoundTouchOptionsFlow:
        return BoseSoundTouchOptionsFlow()

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
                    options={
                        CONF_ENABLE_VOLUME_FADE: user_input[CONF_ENABLE_VOLUME_FADE],
                        CONF_VOLUME_FADE_DURATION: user_input[CONF_VOLUME_FADE_DURATION],
                    },
                )

        data_schema = vol.Schema(
            {vol.Required("host"): str, **_volume_schema(user_input or {})}
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


class BoseSoundTouchOptionsFlow(config_entries.OptionsFlow):
    """Configure fading without reloading or losing the current HA volume target."""

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(_volume_schema(dict(self.config_entry.options))),
        )
