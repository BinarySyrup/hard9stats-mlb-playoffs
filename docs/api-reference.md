# API Reference

The interactive API reference is available at `/docs` while the service is running. All report routes use one of the series codes `WCS`, `LDS`, `LCS`, or `WS`. Report endpoints require no request body.

## Health

### `GET /health`

Returns `{"status":"ok"}`. This is a basic process health response; it does not check the configured agent endpoint or report data.

## Screenshot ingestion

### `POST /ingest/screenshot`

Send `multipart/form-data` with an image in the required `image` field, a required `data_type`, and a required `series_type`. The selected type determines which extraction prompt is used.

```bash
curl -X POST "http://127.0.0.1:8000/ingest/screenshot" \
  -F "image=@./odds-screenshot.png" \
  -F "data_type=odds" \
  -F "series_type=WCS"
```

`data_type` accepts `odds`, `scores`, or `schedules`; `series_type` accepts `WCS`, `LDS`, `LCS`, or `WS`. The service sends the matching prompt from `data/llm-prompts` and asks Ollama for JSON. The response must be a valid JSON object, but its fields are not checked against a strict extraction schema before saving. Output is saved to the matching `data/ingested/{SERIES}/{data_type}/` folder. The success response includes `request_id`, `created_at`, `source_image_name`, `data`, `warnings`, `confidence`, `agent_metadata`, `extraction_type`, `series_type`, `saved_file_path`, and `saved_file_paths`. Uploaded images are not retained.

The expected extracted data shape is type-specific. Odds use `data.games[]` entries with a `date` (`YYYY-MM-DD`) and no `start_time`; score and schedule games also carry their own `date` (`YYYY-MM-DD`). Score and schedule JSON no longer includes a top-level screenshot `date`. For the ingestion response, score and schedule `data` contains `games` only; warnings, confidence, and extraction metadata remain at the response top level.

Common errors: `400` for a non-image or empty upload; `422` for missing or unsupported `data_type`/`series_type`; `500` when a required prompt file or Ollama configuration is missing; `502` when Ollama is unreachable or returns an unusable response, such as empty content or invalid JSON; `504` when the local inference request times out.

## Merge report data

### `POST /reports/{series_type}/merge-json`

Reads odds JSON files from `data/ingested/{SERIES}/odds/`, scores from `data/ingested/{SERIES}/scores/`, and schedules from `data/ingested/{SERIES}/schedules/`. The odds directory is required; scores and schedules are optional. The response includes `series_type`, `report_date`, `games_count`, and `merged_json_path`.

```bash
curl -X POST "http://127.0.0.1:8000/reports/WCS/merge-json"
```

Returns `404` if the required odds input directory is missing. The merge behavior and file replacement warning are documented in [Report data and workflow](reporting.md).

## Generate report HTML

### `POST /reports/{series_type}/generate-html`

Reads `data/reports/{SERIES}/report-merged.json`, writes an HTML file named with the current server-local generation date, and returns `series_type`, `report_date`, `games_count`, `merged_json_path`, and `html_report_path`.

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
