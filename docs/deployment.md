# Deployment

## Runtime and installation

The project requires Python 3.14. The checked-in lock files are for Windows with CPython 3.14; generate and maintain a target-specific lock for another operating system.

After installing dependencies from the deployment's lock file, install the project from the repository root:

```bash
python -m pip install --no-deps .
```

Start without development reload mode:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Keep the process working directory at the repository root. Persist `data/ingested/` and `data/reports/` without mounting over `data/llm-prompts/`; report paths are relative to the working directory. Back up the runtime data volumes according to your retention needs. The application must be able to reach the Ollama server at `OLLAMA_BASE_URL`; when running in a container, `localhost` refers to that container, not the host running Ollama.

Include the prompt files under `data/llm-prompts` in the deployed application. Typed screenshot ingestion fails if its selected prompt file is unavailable.

## Security and operations

- The app does not implement authentication or rate limiting. Put it behind an authenticated gateway or keep it on a trusted private network.
- Enforce HTTPS and an upload-size limit at the gateway. The screenshot endpoint reads the full upload into memory and sends it to the configured Ollama server.
- Keep the Ollama server private to trusted clients. The application sends screenshot contents to the configured Ollama endpoint.
- Monitor agent availability and filesystem capacity. `/health` only returns process health and does not probe those dependencies.
- Restrict write access to the application data volume. A report merge deletes existing `.json` files in that series' report directory before writing the new merged report.
