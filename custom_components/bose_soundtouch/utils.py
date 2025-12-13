"""Helper utilities for Bose SoundTouch integration."""

from __future__ import annotations

from collections.abc import Iterable

from .client import SoundTouchZoneMember


def _normalize_mac(mac: str | None) -> str:
    return (mac or "").strip().lower()


def speaker_in_zone(
    members: Iterable[SoundTouchZoneMember | dict | str] | None,
    mac_address: str | None,
) -> bool:
    """Return True if the provided MAC belongs to the member list."""

    normalized = _normalize_mac(mac_address)
    if not normalized:
        return False
    for member in members or []:
        candidate: str | None
        if isinstance(member, SoundTouchZoneMember):
            candidate = member.mac
        elif isinstance(member, dict):
            candidate = member.get("mac")  # type: ignore[arg-type]
        else:
            candidate = str(member)
        if _normalize_mac(candidate) == normalized:
            return True
    return False


def same_zone_members(
    first: Iterable[SoundTouchZoneMember] | None,
    second: Iterable[SoundTouchZoneMember] | None,
) -> bool:
    """Return True if both member lists contain the same MAC addresses."""

    def build_set(items: Iterable[SoundTouchZoneMember] | None) -> set[str]:
        normalized: set[str] = set()
        for member in items or []:
            if member.mac:
                normalized.add(_normalize_mac(member.mac))
        return normalized

    return build_set(first) == build_set(second)
