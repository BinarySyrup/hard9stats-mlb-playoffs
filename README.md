# Hard9Stats MLB Playoffs

A FastAPI service for screenshot ingestion and MLB playoff report generation.

Screenshot extraction uses a local Ollama server with `gemma4:12b` by default. It parses odds, scores, or schedules screenshots using a type-specific prompt in `data/llm-prompts` and saves JSON into the matching report input folder. Game dates are returned per game in a `date` field; score and schedule extraction JSON does not include a top-level screenshot date. Install Ollama and pull the model with `ollama pull gemma4:12b`; see the [Quickstart](docs/quickstart.md) for setup and request examples.

## Documentation

Start with the [documentation index](docs/index.md) for setup, configuration, API usage, report workflow, and deployment.

The interactive API reference is available at `/docs` when the service is running.
