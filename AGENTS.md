# AGENTS.md

This file defines working rules for agents in this repository.

## Project Scope

- FastAPI service for:
  - Screenshot ingestion
  - Merging baseball data into report JSON
  - Generating HTML reports

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