# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [2026-09-30]

### Added
- Added dynamic report merge endpoint `POST /reports/{series_type}/merge-json`.
- Added dynamic report generation endpoint `POST /reports/{series_type}/generate-html`.
- Added report status endpoint `GET /reports/{series_type}/status`.
- Added merged/report status response models for OpenAPI docs.
- Added repository agent guidance in `AGENTS.md`.

### Changed
- Updated `/reports/{series_type}/merge-json` to use no request body and read from:
  - `data/ingested/odds/<SERIES_TYPE>/`
  - `data/ingested/scores/<SERIES_TYPE>/`
  - `data/ingested/schedules/<SERIES_TYPE>/` (optional)
- Updated merge behavior to keep one merged JSON per series:
  - output fixed to `data/reports/<SERIES_TYPE>/report-merged.json`
  - existing `.json` files in that series report folder are removed before write
- Updated `/reports/{series_type}/generate-html` to use no request body and read from:
  - `data/reports/<SERIES_TYPE>/report-merged.json`
- Updated HTML output naming to generation date:
  - `data/reports/<SERIES_TYPE>/report-<generated_date>.html`
- Updated report header date to display generation date.
- Updated report header titles:
  - `2026 MLB Playoffs`
  - `Wild Card Series`
  - `Game Report` on its own row under series title
- Updated logo source in generated series reports to:
  - `../assets/hard9stats-logo.png`
- Updated `TBD` rendering in report cells so values consistently use light-gray styling.

### Fixed
- Fixed merge logic to include schedule-only games (e.g., Game 3 rows) so full series rows are present (WCS now 12 games).
- Fixed team matching between schedule city names and odds abbreviations (e.g., Philadelphia/PHI, New York/NY).
- Added inference for missing game start times in merged rows using series progression so date/time can populate all report rows.

### Documentation
- Updated `README.md` for path-parameter-based report endpoints.
- Added explicit API specs for merge, generate, and status endpoints.
- Added series type definitions:
  - `WCS` (Wild Card Series)
  - `LDS` (League Division Series)
  - `LCS` (League Championship Series)
  - `WS` (World Series)
