# Configuration

Settings can be supplied through environment variables or a local `.env` file in the working directory. Use `.env.example` as the starting point. Keep secrets out of source control.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `Hard9Stats MLB Playoffs API` | FastAPI application title. |
| `APP_ENV` | `dev` | Environment label; the app does not currently change behavior based on this value. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server base URL. The app sends chat requests to `/api/chat`. |
| `OLLAMA_MODEL` | `gemma4:26b` | Local model name used for screenshot extraction. |
| `AGENT_TIMEOUT_SECONDS` | `45` | Timeout for the Ollama inference request. |

Screenshot ingestion requires Ollama to be running and the configured model to be available locally. Pull the model with `ollama pull gemma4:26b` or the corresponding configured model name. Every screenshot request must specify a data type and series type. Odds and scores/schedules ingestion reads its prompts from `data/llm-prompts/mlb-data-ingestion-odds.txt` and `data/llm-prompts/mlb-data-ingestion-schedules-scores.txt`; keep these files available in deployments.

The response schemas are `OddsExtraction` and `ScoresSchedulesExtraction` in `app/models/contracts.py`. The app passes the selected model's JSON schema to Ollama and validates its response with Pydantic. See the [Ollama structured outputs guide](https://docs.ollama.com/capabilities/structured-outputs#python) for the schema pattern. Report input and output paths use the `data/` layout described in [Report data and workflow](reporting.md).
