# Configuration

Settings can be supplied through environment variables or a local `.env` file in the working directory. Use `.env.example` as the starting point. Keep secrets out of source control.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `Hard9Stats MLB Playoffs API` | FastAPI application title. |
| `APP_ENV` | `dev` | Environment label; the app does not currently change behavior based on this value. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server base URL shared by both models. The app sends chat requests to `/api/chat`. |
| `OLLAMA_VISION_MODEL` | `qwen2.5vl:7b` | Local model used to extract data from screenshots. |
| `OLLAMA_REASONING_MODEL` | `gemma4:12b` | Local model used to merge report JSON files. |
| `AGENT_TIMEOUT_SECONDS` | `300` | Timeout for the Ollama inference request. |

The built-in timeout and the checked-in `.env.example` both use 300 seconds. Change `AGENT_TIMEOUT_SECONDS` to override it.

Screenshot ingestion requires Ollama to be running and the configured vision model to be available locally. Report merging uses the configured reasoning model. Pull both models with `ollama pull qwen2.5vl:7b` and `ollama pull gemma4:12b`, or pull the corresponding configured model names. Both roles use the same Ollama server URL. Every screenshot request must specify a data type (`odds`, `scores`, or `schedules`) and series type. Ingestion reads its prompt from the matching file in `data/llm-prompts`: `mlb-data-ingestion-odds.txt`, `mlb-data-ingestion-scores.txt`, or `mlb-data-ingestion-schedules.txt`. Keep these files available in deployments.

Replace the former `OLLAMA_MODEL` setting in existing `.env` files with both `OLLAMA_VISION_MODEL` and `OLLAMA_REASONING_MODEL`; `OLLAMA_MODEL` is no longer read.

Screenshot extraction asks Ollama for JSON and parses the response as a JSON object. The extraction is not validated against the Pydantic extraction schemas in `app/models/contracts.py`; expected fields are described in the selected prompt. Report input and output paths use the `data/` layout described in [Report data and workflow](reporting.md).
