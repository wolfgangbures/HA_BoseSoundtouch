# Summary

This beta improves local Bose SoundTouch source-selection resilience after Bose cloud-service changes.

# What changed

- increased `/select` timeout tolerance and added a single retry for slow local source switches
- prevented transient `SoundTouchError` communication failures from crashing Home Assistant media-player service calls
- added pre-validation against `/sources` so known but unavailable inputs are skipped before `/select` is attempted
- documented the beta in the README changelog and added prerelease notes

# Validation

- diagnostics report no errors in the changed files
- built local beta artifact: `dist/HA_BoseSoundtouch-1.0.7b1-beta.zip`
- verified the zip contains the expected `custom_components/bose_soundtouch` package layout

# Testing requested

- verify `AIRPLAY`, `AUX`, `BLUETOOTH`, and `PRODUCT` source selection against current Bose firmware
- verify unavailable sources log warnings instead of failing automations
- verify zone workflows still refresh state correctly after delayed or failed commands

# Notes

- this beta does not restore Bose cloud-backed features that Bose has removed or restricted
- approver requested in repo guidance: `@wolfgangbures`