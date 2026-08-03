# Summary

This release promotes the 1.0.9b1 playback-state clarity improvements to stable.

# What changed

- keep zero-volume/muted playback mapped to a ready-like idle effective state
- keep grouped speaker role attributes (`standalone`, `master`, `member`)
- keep effective state detail attributes for grouped/ungrouped automation conditions
- documented stable release notes and README changelog entry

# Validation

- diagnostics report no errors in the changed files
- stable tag and GitHub release created from the promoted version

# Testing requested

- verify speaker state does not show active playback when volume is `0`
- verify grouped role attributes remain correct during zone create/join/leave
- verify existing controls (power, volume, source select) behave unchanged

# Notes

- approver requested in repo guidance: `@wolfgangbures`
