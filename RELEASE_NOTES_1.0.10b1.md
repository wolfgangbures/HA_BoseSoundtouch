# Bose SoundTouch 1.0.10b1

This beta adds dedicated sensor entities for tracking key SoundTouch properties in Home Assistant history.

## Highlights

- Adds a `Volume` sensor reporting the current speaker volume in percent.
- Adds an `Input` sensor reporting the currently selected source/input.
- Adds a `Zone` sensor exposing standalone/group state with zone metadata attributes.
- Sensors are coordinator-backed and reuse existing poll data with no additional endpoint traffic.

## Intended validation

- Verify new entities are created after integration reload:
  - `sensor.<speaker>_volume`
  - `sensor.<speaker>_input`
  - `sensor.<speaker>_zone`
- Verify Recorder history charts show changes for volume, input, and zone values.
- Verify existing `media_player` controls and zone services continue working unchanged.

## Upgrade notes

- Manifest version: `1.0.10b1`
- Suggested release tag: `v1.0.10b1`
