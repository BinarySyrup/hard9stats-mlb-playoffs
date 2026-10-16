# Configuration

Settings can be supplied through environment variables or a local `.env` file in the working directory. Use `.env.example` as the starting point. Keep secrets out of source control.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `Hard9Stats MLB Playoffs API` | FastAPI application title. |
| `APP_ENV` | `dev` | Environment label; the app does not currently change behavior based on this value. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server base URL. The app sends chat requests to `/api/chat`. |
| `OLLAMA_MODEL` | `gemma4:12b` | Local model name used for screenshot extraction. |
| `AGENT_TIMEOUT_SECONDS` | `45` | Timeout for the Ollama inference request. |

Screenshot ingestion requires Ollama to be running and the configured model to be available locally. Pull the model with `ollama pull gemma4:12b` or the corresponding configured model name. Every screenshot request must specify a data type (`odds`, `scores`, or `schedules`) and series type. Ingestion reads its prompt from the matching file in `data/llm-prompts`: `mlb-data-ingestion-odds.txt`, `mlb-data-ingestion-scores.txt`, or `mlb-data-ingestion-schedules.txt`. Keep these files available in deployments.

Screenshot extraction asks Ollama for JSON and parses the response as a JSON object. The extraction is not validated against the Pydantic extraction schemas in `app/models/contracts.py`; expected fields are described in the selected prompt. Report input and output paths use the `data/` layout described in [Report data and workflow](reporting.md).
