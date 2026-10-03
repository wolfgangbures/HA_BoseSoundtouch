# Bose SoundTouch 2.0.0b2

Corrects the fade configuration surface: fade enable and duration are now
properties exposed on each speaker device, not integration Configure options.

## Device controls

Under the speaker's device page -> Configuration:

- **Volume fade**: switch, default off. Use `switch.turn_on` / `switch.turn_off`.
- **Volume fade duration**: number, default 1000 ms, range 0-60000 ms in 1 ms
  steps. Use `number.set_value`. Zero means immediate.

Set these controls, then call `media_player.volume_set` once with the final
target. Values apply immediately to subsequent requests; active fades are
not restarted. Controls remain available offline and persist across HA restarts.

## Upgrade

Existing beta 1 enable/duration values are preserved in HA storage. Configure
and onboarding no longer expose these options. Legacy durations greater than
60000 ms remain effective until changed; newly set durations must be within
0-60000 ms.

Target correction, retries, fade cancellation and unload cleanup are unchanged.
Volume targets themselves remain in memory, unlike the persistent fade settings.

## Validation

32 regression tests cover device identity, platform setup, defaults, persistence,
beta 1 compatibility, immediate automation updates, validation, listener cleanup,
and the existing volume controller behavior using lightweight HA substitutes.
Physical speakers and live Home Assistant still require beta validation.

Version: `2.0.0b2`. Tag: `v2.0.0b2`.
