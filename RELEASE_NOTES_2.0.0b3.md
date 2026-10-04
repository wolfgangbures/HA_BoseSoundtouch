# Bose SoundTouch 2.0.0b3

## Persistent volume override

A new per-speaker **Persistent volume override** switch defaults to on.

- **On:** retain the last HA target, retry after volume communication errors,
  and correct later disturbances on every successful poll, as in beta 2.
- **Off:** attempt the requested volume until reached, but stop on the first
  volume read/write error. Do not correct later drift or restore volume after
  a polling outage. Ignored writes without errors are still retried until
  actual volume confirms the target.

The switch immediately affects poll correction and pending requests' error
handling. Healthy active fades are not cancelled. Disabling during an error
backoff stops the retry after its current wait. Re-enabling restores enforcement
of the last requested target on the next successful poll.
The target remains visible as `soundtouch_target_volume` in either mode.

## Separate fade-in and fade-out durations

- **Volume fade-in duration:** default **2000 ms**, used when increasing volume.
- **Volume fade-out duration:** default **400 ms**, used when decreasing volume.
- Both number entities support **0-60000 ms**, step **1 ms**.
- Zero disables fading only for that direction. The existing **Volume fade**
  switch still enables/disables fading for both directions.

Direction is selected from a fresh actual-volume reading. Each request captures
both duration settings so subsequent setting changes do not alter an active fade.

## Upgrade

The original duration entity is renamed to fade-in, retaining its unique ID,
entity ID and saved duration. Saved durations are not replaced with the new
2000 ms default. Fade-out is a new entity defaulting to 400 ms.
All device settings persist across HA restarts and are controllable in automations.
Volume targets remain in memory until entry unload/HA restart.

## Validation

50 automated regressions cover on/off error and drift behavior, backoff toggling,
directional timing, fresh-volume direction selection, zero durations,
entity identity, saved values, persistence and existing volume/entry lifecycle.
Live Home Assistant and physical speaker testing remains required.

Version: `2.0.0b3`. Tag: `v2.0.0b3`.
