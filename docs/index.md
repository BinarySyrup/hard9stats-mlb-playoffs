# Hard9Stats MLB Playoffs Documentation

This guide covers local setup, configuration, API usage, report data, and deployment for the Hard9Stats MLB Playoffs service.

## Start here

- [Quickstart](quickstart.md): install dependencies, configure screenshot ingestion, and start the development server.
- [Architecture](architecture.md): service components, model roles, and data flows.
- [Configuration](configuration.md): environment variables and secrets.
- [API reference](api-reference.md): routes, requests, responses, and common errors.
- [Report data and workflow](reporting.md): series folders, source JSON, merge behavior, and generated files.
- [Deployment](deployment.md): runtime, storage, and security requirements.

Once the service is running, its interactive API reference is available at `/docs`.

## How the app works

The service has two separate workflows:

1. Screenshot ingestion sends an uploaded image to the configured local Ollama vision model and saves the extracted JSON object.
2. Report generation sends odds, scores, and optional schedules from a series folder to the configured Ollama reasoning model, writes merged JSON, then renders HTML from that JSON.

Screenshot ingestion does not automatically place extracted data into a report's series folders. See [report data and workflow](reporting.md) for the expected layout.
