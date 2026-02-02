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
- Zone automation is handled by three new services available under the `bose_soundtouch` domain:
	- `create_zone`: define a master and the exact list of members that should stay in the group.
	- `join_zone`: append one or more speakers to the master’s current zone without disturbing existing members.
	- `leave_zone`: remove one or more speakers from the master’s zone.
	Each service expects entity IDs from this integration (`media_player.bose_*`).
- Every entity exposes attributes with the active IP address, MAC/device ID, and a JSON-style list of current zone members so automations can react to topology changes.
