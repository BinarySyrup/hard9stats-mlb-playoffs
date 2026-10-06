# Hard9Stats MLB Playoffs

Hard 9 Stats MLB Playoffs data in ingestion and report generation.

## API Endpoints

- `GET /health`
- `POST /ingest/screenshot`
- `POST /reports/{series_type}/merge-json`
- `POST /reports/{series_type}/generate-html`
- `GET /reports/{series_type}/status`

## Directory Convention (Series Type)

Use a `series_type` path variable (for example `WCS`, `LDS`, `LCS`, `WS`) to separate ingested and report artifacts.

Series type definitions:

- `WCS` = `Wild Card Series`
- `LDS` = `League Division Series`
- `LCS` = `League Championship Series`
- `WS` = `World Series`

Recommended structure:

- `data/ingested/<SERIES_TYPE>/odds/`
- `data/ingested/<SERIES_TYPE>/schedules/`
- `data/ingested/<SERIES_TYPE>/scores/`
- `data/reports/<SERIES_TYPE>/`

## Git Tracking for Data Folders

The repository uses top-level sentinel files to keep data directory structure in git while ignoring runtime data files:

- `data/ingested/.keep`
- `data/reports/.keep`

Git behavior:

- Files under `data/ingested/` are ignored by default.
- Files under `data/reports/` are ignored by default.
- Files under `data/reports/assets/` are tracked (for example logos/images).

## Setup

Use Python 3.14 only (any 3.14.x release). From the repository root, create a virtual environment and activate it. Activate the environment again whenever you open a new terminal.

### Windows PowerShell

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

With the virtual environment active, install the pinned runtime dependencies and the app in editable mode:

```bash
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

For development and tests, use `requirements-dev.lock` instead; it includes the runtime lock and pinned test dependencies. Keep the lock files synchronized whenever dependencies change in `pyproject.toml`.

The checked-in lock files target Windows with CPython 3.14. For deployment on another operating system, generate and maintain a lock resolved for that target rather than treating these files as cross-platform locks.

Copy `.env.example` to `.env` and populate the agent settings if you plan to use screenshot ingestion:

- `AZURE_AGENT_API_URL`
- `AZURE_AGENT_API_KEY`
- `AZURE_AGENT_MODEL`
- Optional: `AZURE_AGENT_API_VERSION`

## Run

With the virtual environment active, start the development server from the repository root:

```bash
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`. Press `Ctrl+C` in the terminal to stop the server.

## Ingestion Endpoint

`POST /ingest/screenshot` accepts a screenshot image, sends it to an Azure AI Foundry-compatible agent endpoint, and stores the parsed JSON result in `data/ingested/`.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/screenshot" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@./sample-screenshot.png"
```

Saved ingestion files contain:

- `request_id`
- `created_at`
- `source_image_name`
- `data`
- `warnings`
- `confidence`
- `agent_metadata`

## Report Generation (Two-Step API Flow)

### Step 1: Merge schedules + scores + odds into one report JSON

Endpoint: `POST /reports/{series_type}/merge-json`

Behavior:

- No request body is required.
- The API automatically reads from:
  - `data/ingested/<SERIES_TYPE>/odds/`
  - `data/ingested/<SERIES_TYPE>/scores/`
  - `data/ingested/<SERIES_TYPE>/schedules/` (optional; used if directory exists)
- Output is always written to:
  - `data/reports/<SERIES_TYPE>/report-merged.json`
- Existing `.json` files in `data/reports/<SERIES_TYPE>/` are removed first, so only one merged JSON file is stored per series type.

Request example:

```bash
curl -X POST "http://127.0.0.1:8000/reports/WCS/merge-json" \
  -H "accept: application/json"
```

### Step 2: Generate HTML from merged report JSON

Endpoint: `POST /reports/{series_type}/generate-html`

Behavior:

- No request body is required.
- The API reads from:
  - `data/reports/<SERIES_TYPE>/report-merged.json`
- Output is always written to:
  - `data/reports/<SERIES_TYPE>/report-<report_date>.html`

Request example:

```bash
curl -X POST "http://127.0.0.1:8000/reports/WCS/generate-html" \
  -H "accept: application/json"
```

Response includes:

- `series_type`
- `merged_json_path`
- `html_report_path`
- `report_date`
- `games_count`

## API Spec: `POST /reports/{series_type}/merge-json`

Path parameter:

- `series_type` (string): `WCS`, `LDS`, `LCS`, or `WS`.

Request body:

- None.

Success response (`200`):

- `series_type` (string)
- `report_date` (string, `YYYY-MM-DD`, generation date)
- `games_count` (integer)
- `merged_json_path` (string)

Error responses:

- `404` when required input directories (`odds` or `scores`) do not exist for the series type.
- `422` for invalid path parameter shape.

## API Spec: `POST /reports/{series_type}/generate-html`

Path parameter:

- `series_type` (string): `WCS`, `LDS`, `LCS`, or `WS`.

Request body:

- None.

Success response (`200`):

- `series_type` (string)
- `report_date` (string, `YYYY-MM-DD`, generation date)
- `games_count` (integer)
- `merged_json_path` (string)
- `html_report_path` (string)

Error responses:

- `404` when merged JSON does not exist for the series type.
- `422` for invalid path parameter shape.


## API Spec: `GET /reports/{series_type}/status`

Path parameter:

- `series_type` (string): `WCS`, `LDS`, `LCS`, or `WS`.

Behavior:

- Checks `data/reports/<SERIES_TYPE>/report-merged.json`.
- Finds the most recently modified file matching `data/reports/<SERIES_TYPE>/report-*.html`.

Success response (`200`):

- `series_type` (string)
- `merged_json_exists` (boolean)
- `merged_json_path` (string)
- `merged_json_modified_at` (string | null, ISO-8601)
- `latest_html_exists` (boolean)
- `latest_html_path` (string | null)
- `latest_html_modified_at` (string | null, ISO-8601)

Example:

```bash
curl -X GET "http://127.0.0.1:8000/reports/WCS/status" \
  -H "accept: application/json"
```




