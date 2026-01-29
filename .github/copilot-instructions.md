# Bose SoundTouch – AI Guide

## Architecture & Data Flow
- The integration is a single Home Assistant platform located under `custom_components/bose_soundtouch`; entities are registered only for `media_player` per [media_player.py](../custom_components/bose_soundtouch/media_player.py).
- Each config entry stores a shared `SoundTouchClient` and `SoundTouchCoordinator` inside `hass.data[DOMAIN][entry_id]` as shown in [__init__.py](../custom_components/bose_soundtouch/__init__.py); reuse these instead of creating new clients.
- `SoundTouchCoordinator` polls the speaker every `DEFAULT_POLL_INTERVAL` seconds (15s) and exposes a `SoundTouchState` snapshot consumed by the entity and services ([coordinator.py](../custom_components/bose_soundtouch/coordinator.py), [client.py](../custom_components/bose_soundtouch/client.py)).

## Config & Lifecycle
- YAML setup is intentionally unsupported; all onboarding happens through the config flow that validates the host and enforces unique device IDs ([config_flow.py](../custom_components/bose_soundtouch/config_flow.py)).
- `async_setup_entry` must register the custom services exactly once per Home Assistant instance before forwarding the entry to platforms ([__init__.py](../custom_components/bose_soundtouch/__init__.py)).
- Unloading relies on `async_unload_platforms`; avoid storing additional per-entry state outside `hass.data[DOMAIN][entry_id]` so unloading works.

## SoundTouchClient Usage
- The client is fully async and wraps the Bose XML HTTP API via `/info`, `/volume`, `/now_playing`, `/getZone`, `/sources`, `/select`, `/setZone`, and `/removeZoneSlave` endpoints ([client.py](../custom_components/bose_soundtouch/client.py)).
- `async_get_state()` issues the four read requests concurrently via `asyncio.gather`; if you add new endpoints, follow the same pattern to keep I/O parallel.
- Source selection first tries to match human-friendly names, `source`, or `sourceAccount` values; fall back to raw `ContentItem` payloads only when no known source matches (`SoundTouchSource.matches`).
- Zone mutations (`async_set_zone`, `async_remove_zone_member`) require the client to know its own MAC; always call `_ensure_identified()` or reuse the coordinator-provided state before issuing zone commands.

## Zone & Entity Conventions
- Three domain services (`create_zone`, `join_zone`, `leave_zone`) live in [__init__.py](../custom_components/bose_soundtouch/__init__.py) with schemas mirrored in [services.yaml](../custom_components/bose_soundtouch/services.yaml); extend them here if new workflows are needed.
- `_async_apply_zone_service` normalizes members, prevents masters from joining themselves, and calls `same_zone_members` to short-circuit no-op updates ([utils.py](../custom_components/bose_soundtouch/utils.py)). Respect this dedupe logic when altering zone behavior.
- `SoundTouchMediaPlayer` caches MAC→entity mappings and the last known zone topology in `hass.data[DOMAIN][DATA_MAC_LOOKUP]` and `[DATA_ZONE_CACHE]`; reuse these caches when you need entity references for MAC addresses ([media_player.py](../custom_components/bose_soundtouch/media_player.py)).
- Extra attributes expose both raw zone membership and resolved entity IDs so automations can reason about groups; keep these attributes backward-compatible when making changes.

## Media Player Behavior
- The entity exposes `TURN_ON`, `TURN_OFF`, `VOLUME_SET`, and `SELECT_SOURCE`; power uses a press/release pair on the `POWER` key, so new key actions should follow the `_async_power_cycle` pattern.
- Audio states convert Bose `playStatus` strings into Home Assistant `MediaPlayerState`; add new mappings by updating `_normalize` logic inside `state` rather than sprinkling checks elsewhere.
- Volume methods clamp to 0-100 and immediately request a coordinator refresh; keep this "act then refresh" approach whenever you add setters so UI state stays in sync.

## Developer Workflow
- Manual testing happens inside a Home Assistant instance: copy `custom_components/bose_soundtouch` into `/config/custom_components/`, restart HA, then add the integration via **Settings → Devices & Services** with the speaker host ([README.md](../README.md)).
- Use Home Assistant's **Developer Tools → Services** panel to exercise the custom `bose_soundtouch.*` services; they expect entity IDs from this integration.
- Enable HA debug logging for `custom_components.bose_soundtouch` when troubleshooting HTTP traffic; the client raises `SoundTouchError` on any XML/API issue, which surfaces as `UpdateFailed` inside the coordinator.

## Adding Features Safely
- Prefer extending `SoundTouchState` and the coordinator to expose new device data, then read it inside the entity instead of performing extra HTTP calls per entity update.
- Maintain async-only flows; never call blocking libraries or create new `ClientSession` objects—reuse `async_get_clientsession` and the existing client.
- When exposing new services or options, update `services.yaml`, add schema validation with `vol.Schema`, and ensure `_async_refresh` runs against every affected coordinator so UI state reflects the change immediately.


## GitHub
- Always split branches by feature/fix for PRs; avoid working directly on `main`.
- Write clear, descriptive commit messages; reference related issues/PRs when applicable.
- Merge PRs after the changes immediately.
- Tag releases in GitHub matching the version in `manifest.json`.
- increment the version in `manifest.json` for every PR that changes functionality.