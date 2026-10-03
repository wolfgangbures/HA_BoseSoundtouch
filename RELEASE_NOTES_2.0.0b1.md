# Bose SoundTouch 2.0.0b1

Major-version beta for reliable HA volume targets and native volume fading.

## Reliable volume targets

- Every accepted HA volume request replaces the speaker's internal HA target.
- Check actual volume and retry ignored or failed writes until it is confirmed.
- Correct later volume drift on every successful poll, not only after outages.
- Volume targets no longer expire after ten minutes. Zone recovery keeps its
  existing ten-minute policy and polling failure tolerance is unchanged.
- Failed communications are logged and retried with backoff capped at 15 seconds.
- The `soundtouch_target_volume` attribute reports the HA target (0-100).
  Existing volume entities/sensors continue to report actual speaker volume.

## Native fading

Configure each speaker under **Settings -> Devices & Services -> Configure**:

| Option | Default | Meaning |
| --- | --- | --- |
| Enable volume fade | Disabled | Fade each new HA volume request |
| Volume fade duration (ms) | 1000 | Non-negative integer; 0 means immediate |

Fading starts from a fresh speaker-volume reading and sends linear, integer
steps on a 100 ms cadence, plus a final deadline step. A newer request cancels
the old fade. Network latency
may extend the configured duration. The final volume is verified and retried.
An interrupted fade resumes with direct target correction after recovery.
Regular polls do not override an active fade with its final target.

## Compatibility and lifecycle

- Fading is opt-in; existing entries retain immediate writes and refreshes.
- Option changes apply to subsequent requests without dropping the HA target.
- Entry unload cancels volume work.
- Targets are in memory and reset on entry unload or HA restart; no volume is
  enforced until the first HA request. Physical buttons or other controllers
  may be overridden once HA has a target.
- HA may reject service calls for unavailable entities before the integration
  receives them. Only accepted requests can be retained and retried.
- Empty, missing or invalid volume responses now raise an explicit error rather
  than appearing to confirm volume zero.

## Validation

Automated tests execute the production client, coordinator, configuration flows,
entity volume method and setup/unload paths with minimal HA substitutes.
They cover ignored/failed writes, capped retry backoff, later drift, existing
polling tolerance, exact fade steps/duration, zero-volume fades, new-request
cancellation, options and invalid device responses.

Run:

```text
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

This is a prerelease. Live Home Assistant and physical speaker validation is
still required, particularly for grouped speakers, network interruptions and
device-specific fade smoothness.

Manifest version: `2.0.0b1`. Release tag: `v2.0.0b1`.
