# AGENTS.md

This file defines working rules for agents in this repository.

## Project Scope

- FastAPI service for:
  - Screenshot ingestion
  - Merging baseball data into report JSON
  - Generating HTML reports

## Series Types

Use these series codes consistently in paths and APIs:

- `WCS` = Wild Card Series
- `LDS` = League Division Series
- `LCS` = League Championship Series
- `WS` = World Series

## Directory Conventions

Use series-separated folders:

- `data/ingested/odds/<SERIES_TYPE>/`
- `data/ingested/schedules/<SERIES_TYPE>/`
- `data/ingested/scores/<SERIES_TYPE>/`
- `data/reports/<SERIES_TYPE>/`

## Report APIs (Current Contract)

### `POST /reports/{series_type}/merge-json`

- No request body.
- Reads inputs dynamically from:
  - `data/ingested/odds/{series_type}`
  - `data/ingested/scores/{series_type}`
  - `data/ingested/schedules/{series_type}` (if present)
- Writes merged output to:
  - `data/reports/{series_type}/report-merged.json`
- Keep only one merged JSON per series:
  - Remove existing `.json` files in `data/reports/{series_type}/` before writing.

### `POST /reports/{series_type}/generate-html`

- No request body.
- Reads merged JSON from:
  - `data/reports/{series_type}/report-merged.json`
- Writes HTML to:
  - `data/reports/{series_type}/report-<generated_date>.html`
- The top-right report date in HTML must use generation date.

### `GET /reports/{series_type}/status`

- Returns existence + metadata for merged JSON and latest report HTML for that series.

## Merge/Report Behavior Rules

- Include all games expected for the series set (for WCS this can be 12 rows: 4 matchups x 3 games).
- If odds are missing for a scheduled game, include the row with `TBD` odds values.
- `TBD` values in report tables must render in light gray style (`trend-value tbd`).
- Prefer canonical team names from odds data when joining schedule-only rows.

## Editing Guidance

- Preserve backward-compatible behavior unless user asks otherwise.
- Keep changes focused and minimal.
- Update `README.md` when endpoint contracts or file-path behavior changes.
