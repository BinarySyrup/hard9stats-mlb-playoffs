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

Each source file should contain a `games` array at its root or under `data.games`. Odds records need team names, a series identifier, moneyline and run-line values for both teams, and total-run data. Score and schedule records are joined to odds by team names and game number; schedule records can also provide game number, start time, venue, status, and series metadata.

Screenshot-ingestion JSON is saved separately to `INGESTED_OUTPUT_DIR`. It is not automatically split into odds, schedule, or score files.

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

Runtime data files are ignored by Git. Back up or persist `data/` separately if the artifacts must survive redeployments.
