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

Keep the process working directory at the repository root and mount `data/` on persistent storage. Report input and output paths are relative to the working directory. Back up the volume according to your retention needs.

## Security and operations

- The app does not implement authentication or rate limiting. Put it behind an authenticated gateway or keep it on a trusted private network.
- Enforce HTTPS and an upload-size limit at the gateway. The screenshot endpoint reads the full upload into memory and forwards it to the configured agent endpoint.
- Store agent credentials in deployment secrets, not in source control or image layers.
- Monitor agent availability and filesystem capacity. `/health` only returns process health and does not probe those dependencies.
- Restrict write access to the application data volume. A report merge deletes existing `.json` files in that series' report directory before writing the new merged report.
