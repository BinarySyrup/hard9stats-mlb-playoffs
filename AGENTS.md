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

Use series-first folders for ingested data:

- `data/ingested/<SERIES_TYPE>/odds/`
- `data/ingested/<SERIES_TYPE>/schedules/`
- `data/ingested/<SERIES_TYPE>/scores/`
- `data/reports/<SERIES_TYPE>/`

## Report APIs (Current Contract)

### `POST /reports/{series_type}/merge-json`

- No request body.
- Reads inputs dynamically from:
  - `data/ingested/{series_type}/odds`
  - `data/ingested/{series_type}/scores`
  - `data/ingested/{series_type}/schedules` (if present)
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

- Keep all games expected for the series set in merged JSON (for WCS this can be 12 rows: 4 matchups x 3 games).
- Keep scheduled games without odds in merged JSON with `TBD` odds values, but omit their game rows from generated HTML.
- If a game has some odds data, render its row and show missing odds values in light gray style (`trend-value tbd`).
- Prefer canonical team names from odds data when joining schedule-only rows.

## Editing Guidance

- Preserve backward-compatible behavior unless user asks otherwise.
- Keep changes focused and minimal.
- Update `README.md` when endpoint contracts or file-path behavior changes.

## Brand

- Before changing UI, styling, copy, or visual assets, read `BRAND.md` and follow its guidance.

## Workflow

- Ask before searching the web.
- Do not start the app, run app code, build, or test unless the user explicitly asks.
- Do not commit changes unless the user explicitly asks.
- Update `README.md` when the documented stack, setup, or project structure changes.