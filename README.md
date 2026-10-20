# Hard 9 Stats - MLB Playoffs

Hard 9 Stats provides analytics for MLB postseason sports-market stats. 

[Hard 9 Stats Website](https://www.hard9stats.com)

A Python FastAPI service for MLB postseason sports-market stats analytics report.

## Tech Stack

| Area | Technology |
| --- | --- |
| API runtime | Python 3.14; FastAPI 0.141.1; Uvicorn 0.54.0 |
| Validation and settings | Pydantic 2.13.5; Pydantic Settings 2.15.0 |
| Screenshot uploads | `python-multipart` 0.0.32 |
| Ollama client | Ollama `/api/chat` via HTTPX 0.28.1; server is configured separately |
| Vision model | `qwen2.5vl:7b` by default |
| Reasoning model | `gemma4:12b` by default |
| API test suite | Pytest 9.1.1; FastAPI TestClient; isolated temporary directories; mocked Ollama calls |

## Documentation

Start with the [documentation index](docs/index.md) for setup, configuration, API usage, report workflow, and deployment. The interactive API reference is available at `/docs` when the service is running.

## How it works

Screenshot ingestion extracts odds, scores, or schedules into JSON. User captures odds screenshots from sportsbook websites such as DraftKings and schedules & scores screenshots from sports websites such as ESPN. See sample files in [docs/samples](docs/samples).

Report merging combines those JSON inputs into a series report, and HTML generation renders the merged report.

The service uses two local Ollama models:

- Vision: `qwen2.5vl:7b` by default, for screenshot extraction.
- Reasoning: `gemma4:12b` by default, for merging report JSON.

Configure them with `OLLAMA_VISION_MODEL` and `OLLAMA_REASONING_MODEL`. Both use the server URL in `OLLAMA_BASE_URL`. See `.env.example` and the [Quickstart](docs/quickstart.md) to install and configure Ollama.

## API at a glance

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check that the service process is responding. |
| `POST` | `/ingest/{series_type}/{data_type}/` | Extract screenshot data and save it to the matching series input folder. |
| `POST` | `/reports/{series_type}/merge-json` | Merge the series' ingested JSON files. |
| `POST` | `/reports/{series_type}/generate-html` | Generate HTML from the merged report. |
| `GET` | `/reports/{series_type}/status` | Check merged JSON and generated HTML artifacts. |

For screenshot ingestion, `series_type` is `WCS`, `LDS`, `LCS`, or `WS`; `data_type` is `odds`, `scores`, or `schedules`. Send the screenshot as the `image` multipart field. The former `/ingest/screenshot` endpoint has been removed. The `/reports` endpoint paths are unchanged. The [API reference](docs/api-reference.md) lists series aliases and request and response details.

Example: ingest an odds screenshot for the Wild Card Series.

```bash
curl -X POST "http://127.0.0.1:8000/ingest/WCS/odds/" \
  -F "image=@./odds-screenshot.png"
```

Ingested files are stored under `data/ingested/{series_type}/{data_type}/`. Merged JSON and generated HTML are stored under `data/reports/{series_type}/`.

Odds extraction JSON stores game objects in screenshot order in the top-level `games` array, alongside `warnings` and `confidence`. Each team's moneyline price is numeric `moneyline.odds`; trends are derived from the paired prices, with the lower numeric price marked Favorite and missing or equal prices marked `TBD`. Each game's total is stored once at `odds.total`, with `line`, `over_odds`, and `under_odds`, separate from the away and home team markets. Score and schedule extraction also stores `screenshot_date` when visible, and places postseason game number and league in `series.game` and `series.league`.
