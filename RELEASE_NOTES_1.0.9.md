# Bose SoundTouch 1.0.9

Stable release promoting the 1.0.9b1 playback-state and group-awareness improvements.

## Highlights

- Keeps refined state mapping so speakers reporting `Playing` while volume is `0` (or muted) are surfaced as a ready-like `idle` state.
- Keeps explicit grouping role attributes (`standalone`, `master`, `member`) for clearer automation logic.
- Keeps effective state detail attributes that combine playback and group context.

## Scope

- This release improves state clarity and grouped/standalone differentiation for entity behavior.
- It does not change SoundTouch polling cadence, transport behavior, or zone service APIs.

## Upgrade notes

- Manifest version: `1.0.9`
- Suggested release tag: `v1.0.9`
