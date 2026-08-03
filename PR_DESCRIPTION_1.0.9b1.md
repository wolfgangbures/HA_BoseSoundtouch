# Summary

This beta improves media player state clarity when the speaker is effectively silent and adds explicit group-awareness metadata.

# What changed

- mapped `Playing` with zero volume (or mute) to a ready-like `idle` effective state
- added group role detection for `standalone`, `master`, and `member`
- added effective state attributes for richer grouped/ungrouped automation decisions
- documented the prerelease in README and dedicated release notes

# Validation

- diagnostics report no errors in the changed files
- verify attributes in Home Assistant Developer Tools state panel

# Testing requested

- verify `media_player` state no longer shows active playback at volume `0`
- verify grouped speakers expose expected `soundtouch_group_role` values
- verify zone create/join/leave services behave unchanged

# Notes

- approver requested in repo guidance: `@wolfgangbures`
