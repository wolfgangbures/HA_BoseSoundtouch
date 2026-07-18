<img src="https://raw.githubusercontent.com/wolfgangbures/HA_BoseSoundtouch/main/logo.png" alt="Bose SoundTouch" width="25%" height="25%" />

# Bose SoundTouch custom integration

This integration exposes individual Bose SoundTouch speakers as `media_player` entities without depending on the legacy HTTP platform. It is implemented natively for Home Assistant using an asynchronous HTTP client so it can run entirely inside the core process.

## Features

- Local HTTP control via the public SoundTouch XML API
- Power toggle, volume control and source selection
- Automatic polling via a `DataUpdateCoordinator`
- Zone member awareness plus built-in services for creating/joining/leaving zones

## Installation

1. Copy the `bose_soundtouch` folder into `/config/custom_components/` on your Home Assistant instance.
2. Restart Home Assistant so it can discover the new integration.
3. Navigate to **Settings → Devices & Services → Add Integration** and search for **Bose SoundTouch**.
4. Enter the hostname or IP address of your speaker and submit the form. The integration fetches the device identifier to prevent duplicates.

## Usage tips

- The created `media_player` entity exposes power, volume and source controls directly in the UI.
- Source selection relies on the SoundTouch source identifiers (for example `TUNEIN`, `BLUETOOTH`, `AUX`). Provide the identifiers exactly as they appear in the Bose app or in the `/sources` response for reliable matching.
- The integration only attempts `/select` for sources that the speaker currently reports as selectable. If a source is known but currently unavailable, the command is skipped and only a warning is logged.
- Zone automation is handled by three new services available under the `bose_soundtouch` domain:
	- `create_zone`: define a master and the exact list of members that should stay in the group.
	- `join_zone`: append one or more speakers to the master’s current zone without disturbing existing members.
	- `leave_zone`: remove one or more speakers from the master’s zone.
	Each service expects entity IDs from this integration (`media_player.bose_*`).
- Every entity exposes attributes with the active IP address, MAC/device ID, and a JSON-style list of current zone members so automations can react to topology changes.

## Changelog

### 1.0.8

- Promoted the availability-handling fixes from `1.0.8b1` to stable.
- Keeps coordinator-level transport failure handling so polling errors mark entities unavailable instead of leaving stale state visible.
- Keeps DNS, socket, timeout, and HTTP transport failures mapped to `UpdateFailed` during polling so Home Assistant availability drops correctly.

For stable release notes, see `RELEASE_NOTES_1.0.8.md`.

### 1.0.8b1

- Added coordinator-level transport failure handling so fetch errors mark entities unavailable instead of leaving stale state visible.
- Treats DNS, socket, and HTTP transport failures during polling as `UpdateFailed` so Home Assistant availability drops correctly.
- Built for beta validation of offline/unreachable speaker behavior after transient network failures.

For GitHub prerelease notes, see `RELEASE_NOTES_1.0.8b1.md`.

### 1.0.7

- Promoted the source-selection resilience fixes from `1.0.7b1` to stable.
- Kept `/select` reliability improvements: longer timeout and one retry for slower speaker responses.
- Kept command-path error containment so transient communication issues do not crash Home Assistant scripts.
- Kept source availability pre-validation against `/sources` before attempting `/select`.

For stable release notes, see `RELEASE_NOTES_1.0.7.md`.

### 1.0.7b1

- Added longer timeout handling and a single retry for `/select` requests because newer Bose SoundTouch firmware can stall longer on local source switching.
- Prevented transient SoundTouch communication errors from bubbling out of entity service calls and breaking Home Assistant scripts.
- Added source availability pre-validation so known but unavailable inputs are skipped before `/select` is attempted.
- Built for beta validation of Bose cloud-deprecation related source-selection regressions.

For GitHub prerelease notes, see `RELEASE_NOTES_1.0.7b1.md`.


