# Report Data and Workflow

## `series_type` values

| `series_type` | Series |
| --- | --- |
| `WCS` | Wild Card Series |
| `LDS` | League Division Series |
| `LCS` | League Championship Series |
| `WS` | World Series |

Use these uppercase `series_type` codes in API paths and directory names. The API reference lists the accepted aliases.

## Directory layout

Run the service from the repository root. Report paths are relative to its working directory.

```text
data/
  llm-prompts/
    mlb-data-merge.txt
    mlb-data-ingestion-odds.txt
    mlb-data-ingestion-schedules.txt
    mlb-data-ingestion-scores.txt
  ingested/
    WCS/
      odds/
      schedules/
      scores/
  reports/
    WCS/
      report-merged.json
      report-YYYY-MM-DD.html
```

Repeat the series folders for `LDS`, `LCS`, and `WS`. Place source `.json` files directly in one or more input folders. The merge endpoint reads every file matching `data/ingested/{series_type}/*/*.json`; the folders can be absent, but the endpoint returns `404` if it finds no input JSON files.

Screenshot ingestion uses the configured Ollama vision model and the prompt file matching the `data_type` URL segment. Call `POST /ingest/{series_type}/{data_type}/`, using `odds`, `scores`, or `schedules` for the data type. Each request parses the model response as a JSON object and writes it to the matching series input folder: `odds/`, `scores/`, or `schedules/`. The prompt describes the expected fields; the extraction is not checked against a strict schema before saving.

Every screenshot-ingestion request requires a data type and series type so the matching prompt can be selected and the output written directly to the report input folders.

## Merge, then generate

1. Place schedule, odds, and score JSON files in the matching series folders.
2. Call `POST /reports/{series_type}/merge-json`.
3. Review `data/reports/{series_type}/report-merged.json` and its `games` list.
4. Call `POST /reports/{series_type}/generate-html`.
5. Call `GET /reports/{series_type}/status` to check the output paths and modification times.

The merge sends all input files and `data/llm-prompts/mlb-data-merge.txt` to the configured Ollama reasoning model. It saves the model response directly to `data/reports/{series_type}/report-merged.json` without schema validation. **Before writing, it deletes existing `.json` files in that series' report directory.** Keep other JSON artifacts elsewhere.

## Missing data and rendered rows

The merge can retain scheduled games that have no odds and fill missing odds with `TBD`. It prefers team names from odds when joining schedule-only rows. For the Wild Card Series, full schedule coverage can produce 12 merged games (four matchups, three games each).

The HTML renderer omits games with no odds at all. When some odds exist, it renders the row and displays missing values as `TBD`. Generated HTML uses the generation date in its filename and report header. Generating again on the same server-local date writes to the same filename.

Ingested files and generated reports are runtime data ignored by Git. The prompt files in `data/llm-prompts/` are application inputs and should be kept with the deployed source. Back up or persist the runtime folders separately if artifacts must survive redeployments.
