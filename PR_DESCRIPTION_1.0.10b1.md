# Summary

This beta introduces dedicated sensor entities for SoundTouch volume, input, and zone values so Home Assistant can record full history for those properties.

# What changed

- added a new `sensor` platform for the integration
- added `Volume`, `Input`, and `Zone` sensors backed by coordinator state
- kept polling behavior unchanged by reusing existing coordinator data
- added beta release notes and README changelog entry

# Validation

- diagnostics report no errors in changed files
- beta version and tag naming follow existing repository convention

# Testing requested

- verify sensor entities are created after integration reload
- verify history graphs record value changes for volume, input, and zone
- verify existing media-player and zone service behavior remains unchanged

# Notes

- approver requested in repo guidance: `@wolfgangbures`
