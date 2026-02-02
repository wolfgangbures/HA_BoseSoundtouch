"""Async client for the Bose SoundTouch HTTP API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import asyncio
import logging
import xml.etree.ElementTree as ET

from aiohttp import ClientError, ClientSession
from yarl import URL

from .const import DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)


class SoundTouchError(Exception):
    """Raised when the SoundTouch API returns an error."""


@dataclass(slots=True)
class SoundTouchZoneMember:
    """Represents a member inside the Bose zone."""

    ip: str
    mac: str


@dataclass(slots=True)
class SoundTouchSource:
    """Represents a source entry returned by /sources."""

    name: str
    source: str
    source_account: str | None
    content_type: str | None = None
    location: str | None = None
    is_presetable: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    def matches(self, value: str) -> bool:
        candidate = value.lower()
        options = {
            (self.source_account or "").lower(),
            (self.source or "").lower(),
        }
        if self.name:
            options.add(self.name.lower())
        return candidate in options


@dataclass(slots=True)
class SoundTouchState:
    """Container with the current SoundTouch state."""

    device_id: str
    name: str
    device_type: str
    volume: int
    target_volume: Optional[int]
    is_muted: bool
    source: Optional[str]
    source_account: Optional[str]
    status: Optional[str]
    zone_members: list[SoundTouchZoneMember]
    is_master: bool
    zone_master_mac: Optional[str]
    ip_address: Optional[str]


class SoundTouchClient:
    """Small helper around the Bose SoundTouch XML API."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._session = session
        self._host = host
        self._port = port
        self._base = URL.build(scheme="http", host=host, port=port)
        self._device_id: str | None = None
        self._name: str | None = None
        self._device_type: str | None = None
        self._control_ip: str = host

    @property
    def host(self) -> str:
        return self._host

    @property
    def control_ip(self) -> str:
        return self._control_ip or self._host

    @property
    def device_id(self) -> str | None:
        return self._device_id

    async def async_get_state(self) -> SoundTouchState:
        info_task = asyncio.create_task(self._async_get_info())
        vol_task = asyncio.create_task(self._async_get_volume())
        now_playing_task = asyncio.create_task(self._async_get_now_playing())
        zone_task = asyncio.create_task(self._async_get_zone())
        info, volume, now_playing, zone_details = await asyncio.gather(
            info_task, vol_task, now_playing_task, zone_task
        )
        status = now_playing.get("status") if now_playing else None
        source = now_playing.get("source") if now_playing else None
        source_account = now_playing.get("source_account") if now_playing else None
        master_mac = zone_details["master"] or None
        members = zone_details["members"]
        device_mac = info["device_id"]
        is_master = bool(master_mac) and master_mac.lower() == device_mac.lower()
        return SoundTouchState(
            device_id=device_mac,
            name=info["name"],
            device_type=info["type"],
            volume=volume["actual"],
            target_volume=volume.get("target"),
            is_muted=volume.get("mute", False),
            source=source,
            source_account=source_account,
            status=status,
            zone_members=members,
            is_master=is_master,
            zone_master_mac=master_mac,
            ip_address=self.control_ip,
        )

    async def async_identify(self) -> dict[str, str]:
        """Fetch basic info about the device."""

        return await self._async_get_info()

    async def async_set_volume(self, volume: int) -> None:
        _LOGGER.info(
            "Setting volume on %s (%s) to %s",
            self._name or self._host,
            self._device_id or "unknown",
            volume,
        )
        root = ET.Element("volume")
        root.text = str(volume)
        await self._request("post", "/volume", root)

    async def async_press_key(self, button: str, state: str = "press") -> None:
        root = ET.Element("key", state=state, sender="HomeAssistant")
        root.text = button.upper()
        await self._request("post", "/key", root)

    async def async_select_source(self, source: str) -> None:
        normalized = source.strip().lower()
        try:
            candidates = await self.async_get_sources()
        except SoundTouchError:
            candidates = []
        for candidate in candidates:
            if candidate.matches(normalized):
                await self.async_select_source_item(candidate)
                return
        await self._select_source_fallback(source)

    async def async_select_source_item(self, source: SoundTouchSource) -> None:
        root = ET.Element("ContentItem")
        if source.source:
            root.set("source", source.source)
        if source.source_account is not None:
            root.set("sourceAccount", source.source_account)
        if source.content_type:
            root.set("type", source.content_type)
        if source.location:
            root.set("location", source.location)
        if source.is_presetable:
            root.set("isPresetable", "true")
        elif "isPresetable" in source.raw:
            root.set("isPresetable", source.raw["isPresetable"])
        if source.name:
            ET.SubElement(root, "itemName").text = source.name
        await self._request("post", "/select", root)

    async def _select_source_fallback(self, source: str) -> None:
        raw_value = (source or "").strip()
        payload = ET.Element("ContentItem")
        if ":" in raw_value:
            source_name, source_account = [part.strip() for part in raw_value.split(":", 1)]
        else:
            source_name, source_account = raw_value, ""
        normalized_source = source_name.upper() if source_name else "AUX"
        payload.set("source", normalized_source)
        if normalized_source == "BLUETOOTH" and not source_account:
            payload.set("sourceAccount", "")
        elif source_account:
            payload.set("sourceAccount", source_account)
        await self._request("post", "/select", payload)

    async def async_set_zone(self, members: list[SoundTouchZoneMember]) -> None:
        await self._ensure_identified()
        zone_root = ET.Element("zone", master=self._device_id or "")
        master_node = ET.SubElement(zone_root, "member", ipaddress=self.control_ip)
        master_node.text = self._device_id or ""
        for member in members:
            node = ET.SubElement(zone_root, "member", ipaddress=member.ip)
            node.text = member.mac
        await self._request("post", "/setZone", zone_root)

    async def async_remove_zone_member(self, member: SoundTouchZoneMember) -> None:
        await self._ensure_identified()
        zone_root = ET.Element("zone", master=self._device_id or "")
        node = ET.SubElement(zone_root, "member", ipaddress=member.ip)
        node.text = member.mac
        await self._request("post", "/removeZoneSlave", zone_root)

    async def _ensure_identified(self) -> None:
        if self._device_id is None:
            await self._async_get_info()

    async def _async_get_info(self) -> dict[str, str]:
        info = await self._request("get", "/info")
        if info is None:
            raise SoundTouchError("Device did not return info payload")
        device_id = info.get("deviceID", "")
        name = info.findtext("name", default="SoundTouch")
        device_type = info.findtext("type", default="")
        ip_address = info.findtext("networkInfo/ipAddress") or info.findtext("ipAddress")
        if ip_address:
            self._control_ip = ip_address.strip()
        self._device_id = device_id
        self._name = name
        self._device_type = device_type
        return {"device_id": device_id, "name": name, "type": device_type}

    async def _async_get_volume(self) -> dict[str, Any]:
        volume = await self._request("get", "/volume")
        if volume is None:
            return {"actual": 0, "mute": False}
        actual = int(volume.findtext("actualvolume", default="0"))
        target_text = volume.findtext("targetvolume")
        mute_text = volume.findtext("mute")
        mute = bool(mute_text and mute_text.lower() == "true")
        data: dict[str, Any] = {"actual": actual, "mute": mute}
        if target_text is not None:
            data["target"] = int(target_text)
        return data

    async def _async_get_now_playing(self) -> dict[str, Any]:
        node = await self._request("get", "/now_playing")
        if node is None:
            _LOGGER.debug("%s: now_playing response was empty", self._host)
            return {}
        content_item = node.find("ContentItem")
        source: str | None = None
        source_account: str | None = None
        if content_item is not None:
            source = (
                content_item.get("source")
                or content_item.findtext("source")
                or content_item.findtext("itemName")
            )
            source_account = content_item.get("sourceAccount") or content_item.findtext("sourceAccount")
        status = node.findtext("playStatus") or node.findtext("status")
        if not status:
            _LOGGER.debug(
                "%s: now_playing missing status (source=%s source_account=%s)",
                self._host,
                source,
                source_account,
            )
        return {"source": source, "source_account": source_account, "status": status}

    async def async_get_sources(self) -> list[SoundTouchSource]:
        node = await self._request("get", "/sources")
        if node is None:
            return []
        sources: list[SoundTouchSource] = []
        for child in list(node):
            attrs = child.attrib
            status = (attrs.get("status") or "").upper()
            if status and status not in {"READY", "PLAYING"}:
                continue
            name = (child.text or attrs.get("itemName") or attrs.get("sourceAccount") or attrs.get("source") or "").strip()
            source = (attrs.get("source") or attrs.get("sourceID") or "").upper()
            source_account = attrs.get("sourceAccount")
            content_type = attrs.get("type") or None
            location = attrs.get("location") or None
            is_presetable = (attrs.get("isPresetable") or "false").lower() == "true"
            sources.append(
                SoundTouchSource(
                    name=name or source_account or source,
                    source=source,
                    source_account=source_account,
                    content_type=content_type,
                    location=location,
                    is_presetable=is_presetable,
                    raw={k: v for k, v in attrs.items()},
                )
            )
        return sources

    async def _async_get_zone(self) -> dict[str, Any]:
        node = await self._request("get", "/getZone")
        members: list[SoundTouchZoneMember] = []
        master_mac = ""
        if node is not None:
            master_mac = node.get("master", "")
            for child in list(node):
                ip = child.get("ipaddress", "")
                mac = (child.text or "").strip()
                if ip and mac:
                    if self._device_id and mac.lower() == self._device_id.lower():
                        self._control_ip = ip
                    members.append(SoundTouchZoneMember(ip=ip, mac=mac))
        return {"members": members, "master": master_mac}

    async def _request(self, method: str, path: str, payload: Optional[ET.Element] = None) -> Optional[ET.Element]:
        url = self._base.with_path(path)
        data: bytes | None = None
        headers: dict[str, str] | None = None
        if payload is not None:
            data = ET.tostring(payload, encoding="utf-8")
            headers = {"Content-Type": "application/xml"}
        try:
            async with self._session.request(method, url, data=data, headers=headers, timeout=10) as resp:
                resp.raise_for_status()
                text = await resp.text()
        except ClientError as err:
            raise SoundTouchError(f"Request to {url} failed: {err}") from err
        if not text.strip():
            return None
        try:
            root = ET.fromstring(text)
        except ET.ParseError as err:
            raise SoundTouchError(f"Unable to parse XML response from {url}: {err}") from err
        errors = root.find("errors")
        if errors is not None:
            raise SoundTouchError(f"Device reported error: {ET.tostring(errors, encoding='unicode')}")
        return root
