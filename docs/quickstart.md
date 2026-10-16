# Quickstart

## Requirements

- Python 3.14.
- The checked-in dependency lock files target Windows with CPython 3.14. For another operating system, use a lock resolved for that platform.
- Ollama installed on the machine that will run inference, with enough RAM/VRAM and disk space for the selected model. Actual resource needs vary with the model build, quantization, and context length.
- The Ollama server must be running and reachable from the app. By default, the app connects to `http://localhost:11434`.
- The configured model must be downloaded locally. The default is `gemma4:12b`.

## Install

Run these commands from the repository root.

### Windows PowerShell

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
Copy-Item .env.example .env
```

For macOS or Linux, create and activate a Python 3.14 virtual environment, then install dependencies from a platform-specific lock file before installing the project with `python -m pip install --no-deps -e .`.

## Configure screenshot ingestion

Install Ollama using the instructions for your operating system, start its server, and pull the selected model:

```bash
ollama pull gemma4:12b
```

Confirm the model is present with `ollama list`. Edit `.env` and set `OLLAMA_BASE_URL` if Ollama is not listening at `http://localhost:11434`; the app process must be able to reach that address. `OLLAMA_MODEL` defaults to `gemma4:12b`. The repository must include the two prompt files in `data/llm-prompts`. Health and report endpoints do not require Ollama. See [Configuration](configuration.md) for all settings.

## Start the development server

```bash
python -m uvicorn app.main:app --reload
```

Check the service and open the interactive API reference:

```bash
curl http://127.0.0.1:8000/health
```

The API reference is at `http://127.0.0.1:8000/docs`. Stop the development server with `Ctrl+C`.

## Ingest a screenshot

For report-ready odds JSON, send the image with `data_type=odds` and its series code:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/screenshot" \
  -F "image=@./odds-screenshot.png" \
  -F "data_type=odds" \
  -F "series_type=WCS"
```

For a scorecard or schedule image, use the combined prompt case:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/screenshot" \
  -F "image=@./scores-schedule-screenshot.png" \
  -F "data_type=scores-schedules" \
  -F "series_type=WCS"
```

`data_type` and `series_type` are required for every screenshot. Odds JSON is saved under `data/ingested/{SERIES}/odds/`. The combined scores/schedules JSON is saved under both `scores/` and `schedules/` for the report merger. The response includes all saved paths. Uploaded images are not retained.
