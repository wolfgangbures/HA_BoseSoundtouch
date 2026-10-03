# Bose SoundTouch 1.0.11b1

This beta hardens the integration against short-lived network hiccups that made speakers go `unavailable` and caused Home Assistant to silently drop volume service calls (e.g. stuck low volumes after a fade script).

## Highlights

- Transient poll failures no longer flip the entity to `unavailable`: the coordinator keeps the last known state for up to 3 consecutive failed polls (`POLL_FAILURE_TOLERANCE`) before reporting `UpdateFailed`.
- Desired volume set via `media_player.volume_set` is remembered and re-applied on the first successful poll after a failure streak.
- Desired zone topology set via `bose_soundtouch.create_zone` / `join_zone` / `leave_zone` is remembered and restored the same way.
- Restore is skipped for intents older than 10 minutes (`DESIRED_STATE_MAX_AGE`) so later manual changes are not overridden.

## Intended validation

- Interrupt the speaker network briefly during a volume fade: the entity should stay available and end up at the requested volume.
- Check the log for `Recovered communication with <host>` followed by `Restoring volume ...` / `Restoring zone membership ...`.
- Verify a real, longer outage still marks the speaker `unavailable` after ~3 failed polls.

## Upgrade notes

- Manifest version: `1.0.11b1`
- Suggested release tag: `v1.0.11b1`
