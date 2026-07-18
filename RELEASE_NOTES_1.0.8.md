# Bose SoundTouch 1.0.8

Stable release promoting the 1.0.8b1 availability-handling fixes for unreachable speakers.

## Highlights

- Keeps coordinator-level transport failure handling so polling errors become `UpdateFailed` instead of leaving the last successful state in place.
- Causes Home Assistant entities to go unavailable on DNS, socket, timeout, and HTTP transport failures during refresh.
- Preserves the earlier source-selection resilience changes while improving offline-speaker behavior.
- Corrects the package branding layout so icon assets are provided from the supported `custom_components/bose_soundtouch/brand/` directory.

## Scope

- This release improves availability correctness when a speaker becomes temporarily unreachable.
- It does not add new recovery behavior beyond the existing coordinator refresh cycle.

## Upgrade notes

- Manifest version: `1.0.8`
- Suggested release tag: `v1.0.8`