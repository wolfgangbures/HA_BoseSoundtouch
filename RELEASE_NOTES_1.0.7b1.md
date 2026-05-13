# Bose SoundTouch 1.0.7b1

This beta focuses on local source-selection reliability after Bose SoundTouch cloud-service changes.

## Highlights

- Increased `/select` tolerance with a longer timeout and one retry for slower local source switches.
- Prevented `SoundTouchError` communication failures from crashing through Home Assistant media-player service calls.
- Added pre-validation against `/sources` so the integration skips sources that the speaker currently reports as unavailable.

## Intended validation

- Verify that selecting `AIRPLAY`, `AUX`, `BLUETOOTH`, or `PRODUCT` sources no longer causes hard script failures when the speaker is slow to respond.
- Verify that temporarily unavailable sources produce warnings instead of failed automations.
- Verify that zone workflows still refresh speaker state correctly after failed or delayed commands.

## Known scope

- This beta does not restore Bose cloud-backed source functionality that Bose has removed or restricted.
- Unknown sources still fall back to raw `/select` requests when they are not present in `/sources`.

## Upgrade notes

- Manifest version: `1.0.7b1`
- Local beta artifact: `dist/HA_BoseSoundtouch-1.0.7b1-beta.zip`