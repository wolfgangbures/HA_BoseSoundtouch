"""Bose SoundTouch custom integration."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import SoundTouchClient, SoundTouchZoneMember
from .const import DOMAIN, PLATFORMS
from .coordinator import SoundTouchCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_CREATE_ZONE = "create_zone"
SERVICE_JOIN_ZONE = "join_zone"
SERVICE_LEAVE_ZONE = "leave_zone"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration via YAML (not supported)."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get("services_registered"):
        _register_services(hass)
        domain_data["services_registered"] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Bose SoundTouch device from a config entry."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get("services_registered"):
        _register_services(hass)
        domain_data["services_registered"] = True

    session = async_get_clientsession(hass)
    client = SoundTouchClient(session, entry.data["host"])
    coordinator = SoundTouchCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    domain_data[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    entity_validator = cv.entity_domain("media_player")

    zone_schema = vol.Schema(
        {
            vol.Required("master"): entity_validator,
            vol.Required("members"): vol.All(cv.ensure_list, [entity_validator]),
        }
    )

    leave_schema = vol.Schema(
        {
            vol.Required("master"): entity_validator,
            vol.Required("members"): vol.All(cv.ensure_list, [entity_validator]),
        }
    )

    async def async_create_zone(call: ServiceCall) -> None:
        _LOGGER.debug(
            "Service bose_soundtouch.%s requested: master=%s members=%s",
            SERVICE_CREATE_ZONE,
            call.data["master"],
            call.data["members"],
        )
        await _async_apply_zone_service(hass, call.data, mode="create")

    async def async_join_zone(call: ServiceCall) -> None:
        _LOGGER.debug(
            "Service bose_soundtouch.%s requested: master=%s members=%s",
            SERVICE_JOIN_ZONE,
            call.data["master"],
            call.data["members"],
        )
        await _async_apply_zone_service(hass, call.data, mode="join")

    async def async_leave_zone(call: ServiceCall) -> None:
        _LOGGER.debug(
            "Service bose_soundtouch.%s requested: master=%s members=%s",
            SERVICE_LEAVE_ZONE,
            call.data["master"],
            call.data["members"],
        )
        await _async_apply_zone_service(hass, call.data, mode="leave")

    hass.services.async_register(DOMAIN, SERVICE_CREATE_ZONE, async_create_zone, schema=zone_schema)
    hass.services.async_register(DOMAIN, SERVICE_JOIN_ZONE, async_join_zone, schema=zone_schema)
    hass.services.async_register(DOMAIN, SERVICE_LEAVE_ZONE, async_leave_zone, schema=leave_schema)


async def _async_apply_zone_service(hass: HomeAssistant, data: dict, mode: str) -> None:
    master_id: str = data["master"]
    member_ids: list[str] = data["members"]
    if master_id in member_ids:
        raise HomeAssistantError("Master speaker cannot also be listed as a member")

    master_entry = _get_entry_data_from_entity(hass, master_id)
    member_entries = [_get_entry_data_from_entity(hass, entity_id) for entity_id in member_ids]

    master_coordinator: SoundTouchCoordinator = master_entry["coordinator"]
    master_client: SoundTouchClient = master_entry["client"]
    master_state = master_coordinator.data
    if not master_state:
        raise HomeAssistantError("Master speaker state is not available yet. Try again shortly.")
    if mode in {"join", "leave"} and not master_state.is_master:
        raise HomeAssistantError("The selected master is not currently leading a zone.")

    current_members = _filter_non_master_members(master_state.device_id, master_state.zone_members)
    members_to_modify = [_entry_to_zone_member(entry) for entry in member_entries]

    if mode == "create":
        target_members = _unique_members(members_to_modify)
    elif mode == "join":
        target_members = _unique_members(current_members + members_to_modify)
    elif mode == "leave":
        remove_set = {member.mac.lower() for member in members_to_modify}
        target_members = [member for member in current_members if member.mac.lower() not in remove_set]
    else:
        raise HomeAssistantError(f"Unsupported zone mode {mode}")

    _LOGGER.debug(
        "Zone %s computed for master %s -> %s",
        mode,
        master_id,
        [f"{member.mac}@{member.ip}" for member in target_members],
    )

    await master_client.async_set_zone(target_members)

    refresh_targets = [master_entry, *member_entries]
    await _async_refresh(refresh_targets)


def _get_entry_data_from_entity(hass: HomeAssistant, entity_id: str) -> dict:
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None or entry.config_entry_id is None:
        raise HomeAssistantError(f"Entity '{entity_id}' is not registered with Bose SoundTouch")
    domain_entries = hass.data.get(DOMAIN, {})
    entry_data = domain_entries.get(entry.config_entry_id)
    if not entry_data:
        raise HomeAssistantError(f"Integration data for '{entity_id}' is unavailable")
    return entry_data


def _entry_to_zone_member(entry_data: dict) -> SoundTouchZoneMember:
    coordinator: SoundTouchCoordinator = entry_data["coordinator"]
    client: SoundTouchClient = entry_data["client"]
    state = coordinator.data
    if not state or not state.device_id:
        raise HomeAssistantError("Speaker information unavailable. Try again once the device is online.")
    return SoundTouchZoneMember(ip=client.control_ip, mac=state.device_id)


def _filter_non_master_members(
    master_mac: str, members: list[SoundTouchZoneMember] | None
) -> list[SoundTouchZoneMember]:
    master_mac_lower = (master_mac or "").lower()
    filtered: list[SoundTouchZoneMember] = []
    for member in members or []:
        mac = (member.mac or "").lower()
        if not mac or mac == master_mac_lower:
            continue
        filtered.append(member)
    return filtered


def _unique_members(members: Iterable[SoundTouchZoneMember]) -> list[SoundTouchZoneMember]:
    unique: dict[str, SoundTouchZoneMember] = {}
    for member in members:
        mac = (member.mac or "").lower()
        if not mac:
            continue
        unique[mac] = member
    return list(unique.values())


async def _async_refresh(entries: Iterable[dict]) -> None:
    tasks = []
    seen: set[int] = set()
    for entry in entries:
        coordinator: SoundTouchCoordinator = entry["coordinator"]
        if id(coordinator) in seen:
            continue
        seen.add(id(coordinator))
        tasks.append(coordinator.async_request_refresh())
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
