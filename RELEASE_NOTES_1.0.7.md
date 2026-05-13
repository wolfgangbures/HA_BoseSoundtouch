# Bose SoundTouch 1.0.7

Stable release promoting the 1.0.7b1 beta reliability fixes for local source selection.

## Highlights

- Improved `/select` resilience with a longer timeout and a single retry for slower local source switching.
- Prevented transient SoundTouch communication errors from crashing through Home Assistant media-player service calls.
- Added source availability pre-validation against `/sources` so known unavailable inputs are skipped before `/select`.

## Scope

- This release improves local control robustness for SoundTouch firmware/cloud-behavior changes.
- It does not restore Bose cloud-backed features that Bose has removed or restricted.

## Upgrade notes

- Manifest version: `1.0.7`
- Suggested release tag: `v1.0.7`
