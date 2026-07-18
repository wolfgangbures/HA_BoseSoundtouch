# Summary

This release promotes the 1.0.8b1 availability fix to stable.

# What changed

- keep coordinator-level transport failure handling for polling
- keep DNS, timeout, socket, and HTTP transport failures mapped to `UpdateFailed`
- keep Home Assistant availability aligned with real speaker reachability during refresh failures
- documented the stable release in the README changelog and release notes

# Validation

- diagnostics report no errors in the changed files
- built local release artifact: `dist/HA_BoseSoundtouch-1.0.8.zip`
- verified the zip contains the expected `custom_components/bose_soundtouch` package layout

# Testing requested

- verify an unreachable speaker becomes unavailable instead of keeping its last known state
- verify availability recovers automatically when connectivity returns
- verify normal source selection and zone flows are unchanged while devices are online

# Notes

- approver requested in repo guidance: `@wolfgangbures`