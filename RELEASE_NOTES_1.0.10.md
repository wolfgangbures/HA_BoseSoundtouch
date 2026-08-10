# Bose SoundTouch 1.0.10

Stable release promoting the sensor additions from 1.0.10b1.

## Highlights

- Adds a `Volume` sensor reporting current speaker volume in percent with full Recorder history.
- Adds an `Input` sensor reporting the currently active source/input.
- Adds a `Zone` sensor exposing standalone/grouped state with `is_master`, `zone_master_mac`, and `zone_size` attributes.
- Sensors are coordinator-backed and produce no additional HTTP polling traffic.

## Upgrade notes

- Manifest version: `1.0.10`
- Suggested release tag: `v1.0.10`
