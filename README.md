# Hard9Stats MLB Playoffs

A FastAPI service for screenshot ingestion and MLB playoff report generation.

Screenshot ingestion uses `POST /ingest/{series_type}/{data_type}/`, with the series and data type in the URL and the image in a multipart field. It uses the `qwen2.5vl:7b` vision model through a local Ollama server by default to parse odds, scores, or schedules screenshots using a type-specific prompt in `data/llm-prompts`, then saves JSON into the matching report input folder. Game dates are returned per game in a `date` field; score and schedule extraction JSON does not include a top-level screenshot date. Report merging uses the `gemma4:12b` reasoning model by default. Install Ollama and pull both models; see the [Quickstart](docs/quickstart.md) for setup and request examples.

Report merging sends all JSON files under `data/ingested/{series_type}/*/` to Ollama using `data/llm-prompts/mlb-data-merge.txt` and the configured reasoning model, then saves the response to `data/reports/{series_type}/report-merged.json`.

## Documentation

Start with the [documentation index](docs/index.md) for setup, configuration, API usage, report workflow, and deployment.

The interactive API reference is available at `/docs` when the service is running.
