# Bose SoundTouch 1.0.8b1

This beta focuses on availability correctness when a SoundTouch speaker becomes unreachable.

## Highlights

- Added coordinator-level transport failure handling so polling errors become `UpdateFailed` instead of leaving the last successful state in place.
- Causes Home Assistant entities to go unavailable on DNS, socket, timeout, and HTTP transport failures during refresh.
- Keeps the previous source-selection resilience changes intact while validating offline-speaker behavior.

## Intended validation

- Verify that unreachable speakers become unavailable in Home Assistant instead of continuing to show their last known state.
- Verify that temporary DNS failures and connection timeouts recover cleanly once the speaker is reachable again.
- Verify that source selection, zoning, and normal polling still behave as before when the speaker is online.

## Known scope

- This beta changes availability behavior during polling failures; it does not add new recovery logic beyond the coordinator refresh cycle.
- Command-path error handling remains unchanged for service calls outside coordinator polling.

## Upgrade notes

- Manifest version: `1.0.8b1`
- Suggested release tag: `v1.0.8b1`
- Local beta artifact: `dist/HA_BoseSoundtouch-1.0.8b1-beta.zip`