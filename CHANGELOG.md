# Changelog

## 0.1.4 - 2026-03-01

- Added `EMPTY` model status for clearly empty build plates
- Added `short_explanation` output field and exposed it in HA state/history
- Added `button.printersentry_force_update` to trigger immediate refresh

## 0.1.3 - 2026-03-01

- Avoided blocking config-entry reloads/options updates by running refresh in background

## 0.1.2 - 2026-03-01

- Changed setup flow to avoid blocking config entry startup on first camera refresh
- Added cancellation handling for RTSP capture refreshes to keep integration running

## 0.1.1 - 2026-03-01

- Fixed Home Assistant startup crash caused by a `name` property conflict in the coordinator
- Added HACS-compliant brand assets and corrected `hacs.json` schema

## 0.1.0 - 2026-03-01

- Initial HACS custom integration release
- Added config flow and options flow for RTSP/Ollama settings
- Added DataUpdateCoordinator-based frame capture + inference pipeline
- Added strict JSON parsing with deterministic HEALTHY/UNHEALTHY mapping
- Added incident detection with consecutive unhealthy threshold
- Added persistent notification support with rate limiting
- Added entities: sensors, binary sensors, and last-frame camera
- Added diagnostics endpoint with credential redaction
- Added history ring buffer with Store-backed restore support
- Added stub services: `pause_print` and `cancel_print`
- Added unit tests for parsing, incident logic, and notification rate limiting
