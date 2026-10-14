# API Reference

The interactive API reference is available at `/docs` while the service is running. All report routes use one of the series codes `WCS`, `LDS`, `LCS`, or `WS`. Report endpoints require no request body.

## Health

### `GET /health`

Returns `{"status":"ok"}`. This is a basic process health response; it does not check the configured agent endpoint or report data.

## Screenshot ingestion

### `POST /ingest/screenshot`

Send `multipart/form-data` with an image in the required `image` field. The configured agent extracts data; the service saves a JSON envelope under `INGESTED_OUTPUT_DIR` (default `data/ingested`).

```bash
curl -X POST "http://127.0.0.1:8000/ingest/screenshot" \
  -F "image=@./sample-screenshot.png"
```

The success response includes `request_id`, `created_at`, `source_image_name`, `data`, `warnings`, `confidence`, `agent_metadata`, and `saved_file_path`. Only the JSON envelope is stored; the image is not retained by the service.

Common errors: `400` for a non-image or empty upload; `422` when extracted confidence data fails schema validation; `502` for an upstream failure or unreadable agent response; `504` for an agent timeout; `500` when required agent configuration is missing.

## Merge report data

### `POST /reports/{series_type}/merge-json`

Reads odds and scores JSON files from `data/ingested/{SERIES}/odds/` and `data/ingested/{SERIES}/scores/`. It also reads schedules from `data/ingested/{SERIES}/schedules/` when that directory exists. The response includes `series_type`, `report_date`, `games_count`, and `merged_json_path`.

```bash
curl -X POST "http://127.0.0.1:8000/reports/WCS/merge-json"
```

Returns `404` if either required input directory is missing. The merge behavior and file replacement warning are documented in [Report data and workflow](reporting.md).

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
