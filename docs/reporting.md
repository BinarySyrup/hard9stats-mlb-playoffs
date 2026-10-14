# Report Data and Workflow

## Series codes

| Code | Series |
| --- | --- |
| `WCS` | Wild Card Series |
| `LDS` | League Division Series |
| `LCS` | League Championship Series |
| `WS` | World Series |

Use these uppercase codes in directory names and API paths.

## Directory layout

Run the service from the repository root. Report paths are relative to its working directory.

```text
data/
  llm-prompts/
    mlb-data-ingestion-odds.txt
    mlb-data-ingestion-schedules-scores.txt
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

Repeat the series folders for `LDS`, `LCS`, and `WS`. Place source `.json` files directly in each input folder. The merge operation requires the odds and scores directories to exist; the schedules directory is optional.

Screenshot ingestion uses the prompt files in `data/llm-prompts`. Select `data_type=odds` or `data_type=scores-schedules` and provide a `series_type` when calling `POST /ingest/screenshot`. Odds JSON is written to the series' `odds/` folder; the combined score/schedule JSON is written to both `scores/` and `schedules/` so the merger can use it for each role. These files contain `games` at the root or under `data.games` and are schema-validated before saving.

Every screenshot-ingestion request requires a data type and series type so its output is validated with the matching schema and written directly to the report input folders.

## Merge, then generate

1. Place odds and score JSON files in the series folders; add schedules when available.
2. Call `POST /reports/{series_type}/merge-json`.
3. Review `data/reports/{SERIES}/report-merged.json` and its `games` list.
4. Call `POST /reports/{series_type}/generate-html`.
5. Call `GET /reports/{series_type}/status` to check the output paths and modification times.

The merge writes `data/reports/{SERIES}/report-merged.json`. **Before writing, it deletes existing `.json` files in that series' report directory.** Keep other JSON artifacts elsewhere.

## Missing data and rendered rows

The merge can retain scheduled games that have no odds and fill missing odds with `TBD`. It prefers team names from odds when joining schedule-only rows. For the Wild Card Series, full schedule coverage can produce 12 merged games (four matchups, three games each).

The HTML renderer omits games with no odds at all. When some odds exist, it renders the row and displays missing values as `TBD`. Generated HTML uses the generation date in its filename and report header. Generating again on the same server-local date writes to the same filename.

Ingested files and generated reports are runtime data ignored by Git. The prompt files in `data/llm-prompts/` are application inputs and should be kept with the deployed source. Back up or persist the runtime folders separately if artifacts must survive redeployments.
