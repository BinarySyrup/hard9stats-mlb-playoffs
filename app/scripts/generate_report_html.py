import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _parse_start_time(value: str) -> tuple[str, str]:
    cleaned = value.replace(" ET", "").strip()
    parsed = datetime.strptime(cleaned, "%Y-%m-%d %I:%M %p")
    return parsed.strftime("%b %d, %Y"), parsed.strftime("%I:%M %p").lstrip("0")


def _safe_parse_start_time(value: str | None) -> tuple[str, str]:
    if not value:
        return "", ""
    try:
        return _parse_start_time(value)
    except ValueError:
        return "", value


def _trend_class(value: str) -> str:
    if value == "Favorite":
        return "trend-value favorite"
    if value == "TBD":
        return "trend-value tbd"
    return "trend-value"


def _normalize_total_line(value: Any) -> str:
    if value is None:
        return "TBD"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _render_row(
    game_number: int,
    game_data: dict[str, Any] | None,
    matchup_label: str,
    away_heading: str,
    home_heading: str,
    include_team_headers: bool,
) -> str:
    team_header_html = f'<thead><tr><th>{away_heading}</th><th>{home_heading}</th></tr></thead>' if include_team_headers else ""
    total_header_html = '<thead><tr><th>Over</th><th>Runs</th><th>Under</th></tr></thead>' if include_team_headers else ""

    if game_data is None:
        return (
            f'<tr><td class="team game-number-cell" rowspan="2">{game_number}</td>'
            f'<td class="subtable-cell" rowspan="2"><table class="subtable" aria-label="{matchup_label} game {game_number} moneyline">'
            f'{team_header_html}'
            '<tbody><tr><td><span class="trend-value tbd">TBD</span><span class="location-value">Away</span></td>'
            '<td><span class="trend-value tbd">TBD</span><span class="location-value">Home</span></td></tr></tbody></table></td>'
            f'<td class="subtable-cell" rowspan="2"><table class="subtable" aria-label="{matchup_label} game {game_number} spread">'
            f'{team_header_html}'
            '<tbody><tr><td><span class="trend-value tbd">TBD</span><span class="location-value">Away</span></td>'
            '<td><span class="trend-value tbd">TBD</span><span class="location-value">Home</span></td></tr></tbody></table></td>'
            f'<td class="subtable-cell" rowspan="2"><table class="subtable" aria-label="{matchup_label} game {game_number} total-runs">'
            f'{total_header_html}'
            '<tbody><tr><td><span class="trend-value tbd">TBD</span></td><td><span class="trend-value tbd">TBD</span></td>'
            '<td><span class="trend-value tbd">TBD</span></td></tr></tbody></table></td></tr>\n'
            '<tr></tr>'
        )

    odds = game_data["odds"]
    game_date, game_time = _safe_parse_start_time(game_data.get("start_time"))
    moneyline_away = odds["moneyline"]["away"]["trend"]
    moneyline_home = odds["moneyline"]["home"]["trend"]
    spread_away = odds["spread"]["away"]["trend"]
    spread_home = odds["spread"]["home"]["trend"]
    total_line = _normalize_total_line(odds["total_runs"].get("line"))

    moneyline_table = (
        f'<table class="subtable" aria-label="{matchup_label} game {game_number} moneyline">'
        f'{team_header_html}'
        '<tbody><tr>'
        f'<td><span class="{_trend_class(moneyline_away)}">{moneyline_away}</span><span class="location-value">Away</span></td>'
        f'<td><span class="{_trend_class(moneyline_home)}">{moneyline_home}</span><span class="location-value">Home</span></td>'
        '</tr></tbody></table>'
    )
    spread_table = (
        f'<table class="subtable" aria-label="{matchup_label} game {game_number} spread">'
        f'{team_header_html}'
        '<tbody><tr>'
        f'<td><span class="{_trend_class(spread_away)}">{spread_away}</span><span class="location-value">Away</span></td>'
        f'<td><span class="{_trend_class(spread_home)}">{spread_home}</span><span class="location-value">Home</span></td>'
        '</tr></tbody></table>'
    )
    total_value_class = "trend-value tbd" if total_line == "TBD" else "trend-value"
    total_table = (
        f'<table class="subtable" aria-label="{matchup_label} game {game_number} total-runs">'
        f'{total_header_html}'
        '<tbody><tr>'
        '<td><span class="trend-value ou-muted">Over</span></td>'
        f'<td><span class="{total_value_class}">{total_line}</span></td>'
        '<td><span class="trend-value ou-muted">Under</span></td>'
        '</tr></tbody></table>'
    )

    game_meta = ""
    if game_date or game_time:
        game_meta = (
            '<span class="game-meta">'
            f'<span class="game-date">{game_date}</span>'
            f'<span class="game-time">{game_time}</span>'
            '</span>'
        )

    return (
        f'<tr><td class="team game-number-cell" rowspan="2"><span class="game-number">{game_number}</span>{game_meta}</td>'
        f'<td class="subtable-cell" rowspan="2">{moneyline_table}</td>'
        f'<td class="subtable-cell" rowspan="2">{spread_table}</td>'
        f'<td class="subtable-cell" rowspan="2">{total_table}</td></tr>\n'
        '<tr></tr>'
    )


def _render_game_block(section_id: str, series_games: dict[int, dict[str, Any]]) -> str:
    game_one = series_games.get(1) or next(iter(series_games.values()))
    away_full = game_one["teams"]["away"]["full_name"]
    home_full = game_one["teams"]["home"]["full_name"]
    matchup_label = f"{away_full} at {home_full}"

    header_cols = '<thead><tr><th class="col-game">Game</th><th class="col-moneyline">Moneyline</th><th class="col-spread">Spread</th><th class="col-total-runs">Total Runs</th></tr></thead>'

    row_1 = _render_row(1, series_games.get(1), matchup_label, away_full, home_full, True)
    row_2 = _render_row(2, series_games.get(2), matchup_label, away_full, home_full, False)
    row_3 = _render_row(3, series_games.get(3), matchup_label, away_full, home_full, False)

    return (
        f'<section class="game" aria-labelledby="{section_id}">\n'
        '    <div class="top">\n'
        f'        <h2 id="{section_id}">{matchup_label}</h2>\n'
        '    </div>\n'
        '    <table>\n'
        f'        {header_cols}\n'
        '        <tbody>\n'
        f'        {row_1}\n'
        f'        {row_2}\n'
        f'        {row_3}\n'
        '        </tbody>\n'
        '    </table>\n'
        '</section>'
    )


def render_report_html(merged_payload: dict[str, Any]) -> str:
    report_date_value = merged_payload.get("generated_report_date") or datetime.now().astimezone().strftime("%Y-%m-%d")
    report_date = datetime.strptime(report_date_value, "%Y-%m-%d")
    report_date_long = report_date.strftime("%B %d, %Y")

    grouped: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    ordered_series: list[str] = []
    for game in merged_payload["games"]:
        series_id = game["series_id"]
        if series_id not in grouped:
            ordered_series.append(series_id)
        grouped[series_id][int(game["game_number"])] = game

    sections: list[str] = []
    for index, series_id in enumerate(ordered_series, start=1):
        sections.append(_render_game_block(f"g{index}", grouped[series_id]))

    joined_sections = "\n\n    ".join(sections)
    report_type = "Wild Card Series"

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>{report_type} &mdash; {report_date_long}</title>
    <style>
        :root {{
            color-scheme: light;
            font-family: Arial, Helvetica, sans-serif;
            color: #1f2937;
            background: #f8fafc;
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; padding: 30px; }}
        main {{ max-width: 980px; margin: 0 auto; }}
        header {{ margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #334155; }}
        h1 {{ margin: 0 0 6px; font-size: 15px; font-weight: bold; letter-spacing: .03em; text-transform: uppercase; color: #0f172a; }}
        .report-header-row {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; }}
        .report-title-group {{ display: flex; flex-direction: column; }}
        .report-subtitle {{ margin: 0; font-size: 15px; color: #0f172a; font-weight: bold; text-transform: uppercase; letter-spacing: .03em; }}
        .brand-logo {{ display: block; width: 100%; max-width: 260px; height: auto; margin: 0 auto 8px; }}
        .brand-subtitle {{ margin: 0 0 4px; font-size: 28px; font-weight: bold; color: #0f172a; }}
        .sub {{ margin: 0; color: #475569; font-size: 14px; white-space: nowrap; font-weight: bold; }}
        .game {{ margin: 0 0 14px; padding: 16px; background: #ffffff; border: 1px solid #dbe4ef; border-radius: 10px; }}
        .top {{ display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }}
        h2 {{ margin: 0; font-size: 18px; color: #0f172a; }}
        table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }}
        th, td {{ padding: 8px 7px; text-align: left; border-bottom: 1px solid #e5edf5; vertical-align: top; }}
        th {{ background: #edf3f8; color: #334155; text-transform: uppercase; font-size: 11px; letter-spacing: .04em; }}
        .game > table th:nth-child(1) {{ width: 17.5%; }}
        .game > table th:nth-child(2), .game > table th:nth-child(3), .game > table th:nth-child(4) {{ width: 27.5%; }}
        .game > table th.col-spread, .game > table th.col-total-runs {{ background: #edf3f8; color: #334155; text-transform: uppercase; font-size: 11px; letter-spacing: .04em; }}
        tr:last-child td {{ border-bottom: 0; }}
        .team {{ font-weight: bold; }}
        .game-number-cell {{ vertical-align: middle; padding-top: 10px; white-space: nowrap; }}
        .game-number {{ display: inline-block; font-weight: bold; margin-right: 8px; vertical-align: top; }}
        .game-date, .game-time {{ display: block; font-size: 11px; color: #7a8797; white-space: nowrap; }}
        .game-meta {{ display: inline-block; vertical-align: top; }}
        .subtable-cell {{ padding: 6px 7px; }}
        .subtable {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12px; }}
        .subtable th, .subtable td {{ padding: 4px 6px; border: 1px solid #dbe4ef; background: #fff; text-align: left; }}
        .subtable tr > *:first-child:nth-last-child(2), .subtable tr > *:first-child:nth-last-child(2) ~ * {{ width: 50%; }}
        .subtable tr > *:first-child:nth-last-child(3), .subtable tr > *:first-child:nth-last-child(3) ~ * {{ width: 33.333%; }}
        .trend-value {{ display: block; font-weight: normal; color: #0f172a; line-height: 1.1; }}
        .trend-value.favorite {{ font-weight: bold; }}
        .trend-value.tbd, .trend-value.ou-muted {{ color: #c5cfdb; font-weight: normal; }}
        .location-value {{ display: block; margin-top: 1px; font-size: 11px; color: #475569; line-height: 1.1; }}
    </style>
</head>
<body>
<main>
    <header>
        <img class=\"brand-logo\" src=\"../assets/hard9stats-logo.png\" alt=\"Hard9Stats\">
        <p class=\"brand-subtitle\">2026 MLB Playoffs</p>
        <div class=\"report-header-row\">
            <div class=\"report-title-group\"><h1>{report_type}</h1><p class=\"report-subtitle\">Game Report</p></div>
            <p class=\"sub\">{report_date_long}</p>
        </div>
    </header>

    {joined_sections}

</main>
</body>
</html>
"""


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".html") if input_path.suffix == ".json" else input_path.parent / "report.html"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate report HTML from merged report JSON.")
    parser.add_argument("input_json", help="Path to merged report JSON file.")
    parser.add_argument("--output-html", help="Path to write HTML report.")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    output_path = Path(args.output_html) if args.output_html else _default_output_path(input_path)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    html = render_report_html(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
