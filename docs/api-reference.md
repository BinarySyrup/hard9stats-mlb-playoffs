# API Reference

The interactive API reference is available at `/docs` while the service is running. All report routes use one of the series codes `WCS`, `LDS`, `LCS`, or `WS`. Report endpoints require no request body.

## Path parameter options 

| Parameter | Used by | Accepted values |
| --- | --- | --- |
| `series_type` | Screenshot ingestion and all report routes | `WCS` (Wild Card Series), `LDS` (League Division Series), `LCS` (League Championship Series), or `WS` (World Series). The aliases `wild-card`/`wildcard`, `division-series`/`divisionseries`, `league-championship-series`/`leaguechampionshipseries`, and `world-series`/`worldseries` are also accepted case-insensitively. |
| `data_type` | Screenshot ingestion only | `odds`, `scores`, or `schedules` (lowercase). |

The `series_type` path value is normalized to its uppercase code for storage paths and responses. In path examples, `{series_type}` represents that code, such as `WCS`.

## Health

### `GET /health`

Returns `{"status":"ok"}`. This is a basic process health response; it does not check the configured agent endpoint or report data.

## Screenshot ingestion

### `POST /ingest/{series_type}/{data_type}/`

Send `multipart/form-data` with an image in the required `image` field. The `series_type` and `data_type` are path parameters; the selected data type determines which extraction prompt is used.

The former `POST /ingest/screenshot` endpoint has been removed. The `/reports` endpoints retain their existing paths.

```bash
curl -X POST "http://127.0.0.1:8000/ingest/WCS/odds/" \
  -F "image=@./odds-screenshot.png"
```

The service sends the matching prompt from `data/llm-prompts` to the configured Ollama vision model and asks for JSON. The response must be a valid JSON object, but its fields are not checked against a strict extraction schema before saving. Output is saved to the matching `data/ingested/{series_type}/{data_type}/` folder. The success response includes `request_id`, `created_at`, `source_image_name`, `data`, `warnings`, `confidence`, `agent_metadata`, `extraction_type`, `series_type`, `saved_file_path`, and `saved_file_paths`. Uploaded images are not retained.

The expected extracted data shape is type-specific. Odds use `data.games[]` entries with a `date` (`YYYY-MM-DD`), team names, odds, and `series_id`. Each game's odds contain `away`, `home`, and `total` sections; team markets use `run_line` and `moneyline`, and the combined total is stored once under `odds.total` with `line`, `over_odds`, and `under_odds`. Moneyline prices use `odds`, and their trends are derived from the paired prices. Odds extraction does not include `start_time`, `game_number`, or `league`. Score and schedule payloads include `screenshot_date` when shown and per-game `date` values. Their postseason game number and league are nested in `series.game` and `series.league`. In the ingestion response, `data` contains `games` and, when available, `screenshot_date`; warnings and confidence remain at the response top level.

Common errors: `400` for a non-image or empty upload; `422` for missing or unsupported `data_type`/`series_type`; `500` when a required prompt file or Ollama configuration is missing; `502` when Ollama is unreachable or returns an unusable response, such as empty content or invalid JSON; `504` when the local inference request times out.

## Merge report data

### `POST /reports/{series_type}/merge-json`

Reads every JSON file matching `data/ingested/{series_type}/*/*.json`, groups files by their immediate subdirectory, and sends the grouped inputs with `data/llm-prompts/mlb-data-merge.txt` to the configured Ollama reasoning model. The model response is saved to `data/reports/{series_type}/report-merged.json` without schema validation. The response includes `series_type`, `report_date`, `games_count`, and `merged_json_path`.

```bash
curl -X POST "http://127.0.0.1:8000/reports/WCS/merge-json"
```

Returns `404` if no matching input JSON files are found and `422` if an input file is not valid JSON. The merge behavior and file replacement warning are documented in [Report data and workflow](reporting.md).

## Generate report HTML

### `POST /reports/{series_type}/generate-html`

Reads `data/reports/{series_type}/report-merged.json`, writes an HTML file named with the current server-local generation date, and returns `series_type`, `report_date`, `games_count`, `merged_json_path`, and `html_report_path`.

```bash
curl -X POST "http://127.0.0.1:8000/reports/WCS/generate-html"
```

Returns `404` if the merged JSON does not exist. The endpoint writes a file; it does not return the HTML document body.

## Report status

### `GET /reports/{series_type}/status`

Returns `series_type`, whether the merged JSON exists, its path and modification time, and whether a generated HTML report exists, along with the latest HTML path and modification time. The latest HTML is selected by modification time. Missing artifacts have `null` metadata.

```bash
curl "http://127.0.0.1:8000/reports/WCS/status"
```
