# Quickstart

## Requirements

- Python 3.14.
- The checked-in dependency lock files target Windows with CPython 3.14. For another operating system, use a lock resolved for that platform.
- Ollama installed on the machine that will run inference, with enough RAM/VRAM and disk space for both configured models. Actual resource needs vary with the model builds, quantization, and context lengths.
- The Ollama server must be running and reachable from the app. By default, the app connects to `http://localhost:11434`.
- The configured vision and reasoning models must be downloaded locally. Defaults are `qwen2.5vl:7b` and `gemma4:12b`, respectively.

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

Install Ollama using the instructions for your operating system, start its server, and pull both default models:

```bash
ollama pull qwen2.5vl:7b
ollama pull gemma4:12b
```

Confirm both models are present with `ollama list`. Edit `.env` and set `OLLAMA_BASE_URL` if Ollama is not listening at `http://localhost:11434`; the app process must be able to reach that address. `OLLAMA_VISION_MODEL` defaults to `qwen2.5vl:7b` for screenshot extraction, and `OLLAMA_REASONING_MODEL` defaults to `gemma4:12b` for merging report JSON. The repository must include the three prompt files in `data/llm-prompts`. Health and report endpoints do not require Ollama. See [Configuration](configuration.md) for all settings.

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

For a scorecard image, use `data_type=scores`:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/screenshot" \
  -F "image=@./scorecard-screenshot.png" \
  -F "data_type=scores" \
  -F "series_type=WCS"
```

For a schedule image, use `data_type=schedules`:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/screenshot" \
  -F "image=@./schedule-screenshot.png" \
  -F "data_type=schedules" \
  -F "series_type=WCS"
```

`data_type` and `series_type` are required for every screenshot. `data_type` accepts `odds`, `scores`, or `schedules`. Each request saves JSON under the matching `data/ingested/{SERIES}/{data_type}/` folder. The response includes the saved path. Uploaded images are not retained.
