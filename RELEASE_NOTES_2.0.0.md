# Bose SoundTouch 2.0.0

Stable release of the tested `2.0.0b3` functionality. No functional changes
from the final beta.

## Reliable volume control

The integration verifies actual speaker volume and retries unconfirmed writes.
The per-speaker **Persistent volume override** switch defaults to on:

- **On:** retain the last accepted HA target, retry after communication errors,
  and correct later disturbances on every successful poll.
- **Off:** attempt the requested volume until reached, but stop on a volume
  read/write error and leave later drift alone.

Re-enabling persistence enforces the last requested target on the next successful
poll. Targets reset on entry unload or HA restart; no volume is forced before
the first accepted HA volume request.

## Native volume fading

Each speaker device exposes configuration entities usable in HA automations:

| Control | Default |
| --- | --- |
| Volume fade switch | Off |
| Persistent volume override switch | On |
| Volume fade-in duration | 2000 ms |
| Volume fade-out duration | 400 ms |

Both durations support 0-60000 ms with 1 ms steps. Zero means immediate for that
direction. Fades start from a fresh actual-volume reading; newer requests cancel
older fades. Network latency can extend the requested duration.

Set the device controls, then call `media_player.volume_set` once with the final
target instead of running a separate HA fade loop.

## Upgrade

- Device settings persist across HA restarts and remain controllable offline.
- Saved beta settings are retained. The original duration entity remains the
  fade-in control with its existing entity ID and saved value.
- Existing saved durations are not reset to the new defaults.
- The `soundtouch_target_volume` attribute reports the HA target on the 0-100
  scale; volume entities and sensors continue to report actual speaker volume.
- HA may reject calls to unavailable entities before the integration receives
  them; only accepted requests can be retained.

## Validation

The final beta passed 50 automated regression tests and was confirmed working
by the user before stable promotion. This release changes only version metadata
and release documentation.

Version: `2.0.0`. Tag: `v2.0.0`.
