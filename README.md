<img src="https://raw.githubusercontent.com/wolfgangbures/HA_BoseSoundtouch/main/logo.png" alt="Bose SoundTouch" width="25%" height="25%" />

# Bose SoundTouch custom integration

This integration exposes individual Bose SoundTouch speakers as `media_player` entities without depending on the legacy HTTP platform. It is implemented natively for Home Assistant using an asynchronous HTTP client so it can run entirely inside the core process.

## Features

- Local HTTP control via the public SoundTouch XML API
- Power toggle, volume control and source selection
- Persistent HA volume target correction and optional native volume fading
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

## Volume targets and fading (2.0)

Each accepted `media_player.volume_set` request becomes that speaker's HA target.
With **Persistent volume override** on (the default), the integration checks
**actual** volume, retries unconfirmed writes, and corrects
later drift on every successful poll (normally every 15 seconds). The target no
longer expires after ten minutes or requires a network outage to trigger correction.
Other volume controllers, including physical buttons, can be overridden.
Targets are held in memory until the next request or entry unload/HA restart;
no volume is forced before the first HA request.

Open the speaker **device page** in **Settings -> Devices & Services**.
Under Configuration, each device exposes four controls usable in automations:

- **Volume fade** switch: defaults to **off**.
- **Persistent volume override** switch: defaults to **on**. When off, volume
  requests still try until the target is reached, but stop on the first volume
  communication error and do not correct later drift or restore volume after outages.
- **Volume fade-in duration** number: defaults to **2000 ms**, used when increasing volume.
- **Volume fade-out duration** number: defaults to **400 ms**, used when decreasing volume.
  Both durations have range **0-60000 ms**, step **1 ms**. Zero means immediate
  for that direction, even if fading is enabled.

These local device properties persist across HA restarts and can be changed
even when the speaker is offline. They are no longer Configure/onboarding
options. Existing beta settings are retained using the same HA storage:
the original duration value and entity unique ID now belong to fade-in. The
existing entity ID (typically `number.your_speaker_volume_fade_duration`) stays
unchanged, even though its display name is now "Volume fade-in duration".
Fade-out starts at 400 ms. A previously saved fade-in duration is not reset;
legacy durations above 60000 ms remain effective until changed, but new values
must be within the number entity's range. Settings apply to the next volume
request; changing them does not restart an active fade. The persistence switch
applies immediately to poll correction and error handling for pending requests.
Turning it off during an error backoff stops the pending retry when that wait
ends; a healthy active fade continues. Turning it back on re-enforces the last
requested target on the next successful poll. No target is invented on startup.

Example automation sequence (replace entity IDs with those on your device):

```yaml
- action: switch.turn_on
  target:
    entity_id: switch.your_speaker_volume_fade
- action: number.set_value
  target:
    entity_id: number.your_speaker_volume_fade_duration
  data:
    value: 2000
- action: number.set_value
  target:
    entity_id: number.your_speaker_volume_fade_out_duration
  data:
    value: 400
- action: media_player.volume_set
  target:
    entity_id: media_player.your_speaker
  data:
    volume_level: 0.35
```

Fades use a fresh actual-volume reading, linear interpolation and integer
volume steps on a 100 ms cadence, plus a final deadline step. Network latency and the speaker's own response
can extend the requested duration. A newer request cancels the previous fade
and starts from a new speaker reading; fades do not block HA service calls.
With fading disabled, the first write and coordinator refresh are awaited as
before; confirmation/retries continue in the background.
After a fade, the final target is verified and retried until confirmed.
With persistence on, communication failures are logged and retried with backoff
up to 15 seconds; an interrupted fade resumes with direct target correction after
recovery. With persistence off, errors are logged and terminate that request.
Normal polls do not jump to the final target while a fade is active.
Fade-in/out duration is chosen from a fresh actual-volume reading, not cached
HA volume, and both timings are captured when each volume request is accepted.
Unloading the entry cancels pending volume work.

The `soundtouch_target_volume` media-player attribute exposes the HA target on
the 0-100 scale; the volume entity/sensor still reports actual speaker volume.
Unavailable speakers cannot receive HA service calls that HA itself rejects;
with persistence on, already accepted targets remain pending during communication outages.

## Changelog

### 2.0.0

- Promote the validated `2.0.0b3` behavior to stable without functional changes.
- Reliable volume target confirmation and optional persistent drift correction.
- Per-speaker device controls for fade enable, persistent override, fade-in
  duration (default 2000 ms) and fade-out duration (default 400 ms).
- Preserve saved settings and existing fade-in entity IDs.

See [RELEASE_NOTES_2.0.0.md](RELEASE_NOTES_2.0.0.md).

### 2.0.0b3

- Add a persistent volume override device switch, default on; off stops on
  volume errors and leaves later disturbances alone.
- Rename the existing duration to fade-in and add a separate fade-out duration.
- Defaults: fade-in 2000 ms, fade-out 400 ms; preserve saved fade-in values and
  existing entity IDs.

See [RELEASE_NOTES_2.0.0b3.md](RELEASE_NOTES_2.0.0b3.md).

### 2.0.0b2

- Replace integration fade options with a switch and duration number belonging
  to each speaker device, controllable through standard HA actions.
- Persist properties across restarts and preserve beta 1 settings.
- Duration control supports 0-60000 ms with 1 ms steps.
- Volume target enforcement and native fade behavior are unchanged.

See [RELEASE_NOTES_2.0.0b2.md](RELEASE_NOTES_2.0.0b2.md).

### 2.0.0b1

- Major-version beta: always reconcile the last accepted HA volume target.
- Add per-speaker optional native volume fading, latest-request cancellation,
  actual-volume confirmation, retries and unload cleanup.
- Reject missing/invalid speaker volume readings instead of treating them as zero.
- Existing installations retain immediate volume changes by default.

For beta release notes, see [RELEASE_NOTES_2.0.0b1.md](RELEASE_NOTES_2.0.0b1.md).

### 1.0.10

- Promoted the sensor additions from `1.0.10b1` to stable.
- Adds dedicated `sensor` entities for SoundTouch volume, input, and zone state to enable Recorder history and graphs.
- Sensors reuse coordinator data with no additional polling traffic.
- Zone sensor includes `is_master`, `zone_master_mac`, and `zone_size` attributes.

For stable release notes, see `RELEASE_NOTES_1.0.10.md`.

### 1.0.10b1

- Adds dedicated Home Assistant `sensor` entities for SoundTouch volume, input, and zone state to enable Recorder history/graphs.
- New sensors reuse coordinator data and do not introduce additional polling traffic.
- Zone sensor includes attributes for role context (`is_master`, `zone_master_mac`, `zone_size`).

For GitHub prerelease notes, see `RELEASE_NOTES_1.0.10b1.md`.

### 1.0.9

- Promoted the playback-state clarity and grouping metadata improvements from `1.0.9b1` to stable.
- Keeps zero-volume playback refinement so speakers do not appear actively playing when effectively silent.
- Keeps explicit grouping attributes and effective state detail attributes for more reliable automations.

For stable release notes, see `RELEASE_NOTES_1.0.9.md`.

### 1.0.9b1

- Adds state refinement for zero-volume playback so `Playing` with volume `0` (or muted) is surfaced as a ready-like idle state in Home Assistant.
- Adds explicit grouping context attributes to distinguish `standalone`, `master`, and `member` speakers.
- Adds effective state detail attributes to help automations differentiate grouped vs ungrouped playback behavior.

For GitHub prerelease notes, see `RELEASE_NOTES_1.0.9b1.md`.

### 1.0.8

- Promoted the availability-handling fixes from `1.0.8b1` to stable.
- Keeps coordinator-level transport failure handling so polling errors mark entities unavailable instead of leaving stale state visible.
- Keeps DNS, socket, timeout, and HTTP transport failures mapped to `UpdateFailed` during polling so Home Assistant availability drops correctly.
- Fixes the integration branding asset layout so icon and logo files ship from the supported `brand/` directory.

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
