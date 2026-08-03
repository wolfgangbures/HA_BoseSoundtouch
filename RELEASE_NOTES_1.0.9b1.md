# Bose SoundTouch 1.0.9b1

This beta focuses on playback-state clarity and group-awareness improvements for Home Assistant entities.

## Highlights

- Refines state mapping so speakers reporting `Playing` while volume is `0` (or muted) are shown as a ready-like `idle` state.
- Adds explicit group role attributes (`standalone`, `master`, `member`) for easier automation logic.
- Adds effective state detail attributes that combine playback and grouping context.

## Intended validation

- Verify that a speaker at zero volume no longer appears as actively playing.
- Verify that grouped speakers expose clear role information (`master`/`member`) and standalone speakers show `standalone`.
- Verify that existing zone commands and source selection behavior are unchanged.

## Known scope

- Home Assistant `media_player` uses standardized states, so ready semantics are represented via `idle` plus detailed attributes.
- This beta does not alter SoundTouch transport, polling cadence, or zone command APIs.

## Upgrade notes

- Manifest version: `1.0.9b1`
- Suggested release tag: `v1.0.9b1`
- Local beta artifact (optional): `dist/HA_BoseSoundtouch-1.0.9b1-beta.zip`
