# Quickstart

## Requirements

- Python 3.14.
- The checked-in dependency lock files target Windows with CPython 3.14. For another operating system, use a lock resolved for that platform.

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

Edit `.env` and set `AZURE_AGENT_API_URL` and `AZURE_AGENT_MODEL`. Set `AZURE_AGENT_API_KEY` if the agent endpoint requires it. See [Configuration](configuration.md) for all supported settings. Health and report endpoints do not require agent credentials.

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

Send an image as multipart form data in the `image` field:

```bash
curl -X POST "http://127.0.0.1:8000/ingest/screenshot" \
  -F "image=@./sample-screenshot.png"
```

The response includes the extracted data and the path where its JSON envelope was saved. The uploaded image itself is not saved by this service.
