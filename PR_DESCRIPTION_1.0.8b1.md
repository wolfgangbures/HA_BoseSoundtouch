# Summary

This beta validates that Bose SoundTouch polling failures correctly mark entities unavailable in Home Assistant.

# What changed

- added coordinator-level transport failure handling for polling
- convert DNS, timeout, socket, and HTTP transport failures into `UpdateFailed`
- preserve the existing command-path resilience behavior while fixing availability reporting
- documented the beta in the README changelog and added prerelease notes

# Validation

- diagnostics report no errors in the changed files
- build local beta artifact: `dist/HA_BoseSoundtouch-1.0.8b1-beta.zip`
- verify the zip contains the expected `custom_components/bose_soundtouch` package layout

# Testing requested

- verify an unreachable speaker becomes unavailable instead of keeping its last known state
- verify availability recovers automatically when connectivity returns
- verify normal source selection and zone flows are unchanged while devices are online

# Notes

- approver requested in repo guidance: `@wolfgangbures`