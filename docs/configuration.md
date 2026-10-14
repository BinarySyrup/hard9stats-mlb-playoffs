# Configuration

Settings can be supplied through environment variables or a local `.env` file in the working directory. Use `.env.example` as the starting point. Keep secrets out of source control.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `Hard9Stats MLB Playoffs API` | FastAPI application title. |
| `APP_ENV` | `dev` | Environment label; the app does not currently change behavior based on this value. |
| `INGESTED_OUTPUT_DIR` | `data/ingested` | Directory for screenshot-ingestion JSON envelopes. |
| `AZURE_AGENT_API_URL` | Empty | Required agent endpoint URL for screenshot ingestion. |
| `AZURE_AGENT_API_KEY` | Empty | Optional API key; send it when required by the endpoint. |
| `AZURE_AGENT_MODEL` | Empty | Required model identifier for screenshot ingestion. |
| `AZURE_AGENT_API_VERSION` | Empty | Optional API version query parameter. |
| `AGENT_EXTRACTION_PROMPT` | Prompt from `.env.example` | Instructions sent with each screenshot. The expected output is JSON with `data`, `warnings`, and `confidence`. |
| `AGENT_TIMEOUT_SECONDS` | `45` | Timeout for the upstream agent request. |

Screenshot ingestion requires both `AZURE_AGENT_API_URL` and `AZURE_AGENT_MODEL`. Missing either prevents ingestion; other endpoints do not call the agent.

`INGESTED_OUTPUT_DIR` applies to screenshot-ingestion envelopes. Report merge inputs and report outputs use the `data/` paths described in [Report data and workflow](reporting.md).
