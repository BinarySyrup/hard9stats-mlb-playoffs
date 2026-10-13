import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
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


def _score_markup(game_data: dict[str, Any], side: str) -> str:
    runs = ((game_data.get("score") or {}).get(side) or {}).get("runs")
    if runs is None or runs == "":
        return ""
    return f'<span class="score-value">{escape(str(runs))}</span>'


def _spread_line_suffix(trend: str, line: Any) -> str:
    if trend != "Favorite" or line is None or line == "":
        return ""
    return f' <span class="spread-line">({escape(_normalize_total_line(line))})</span>'


def _score_leader(game_data: dict[str, Any]) -> str | None:
    score = game_data.get("score") or {}
    away_runs = (score.get("away") or {}).get("runs")
    home_runs = (score.get("home") or {}).get("runs")
    if away_runs is None or home_runs is None:
        return None

    try:
        away_value = float(away_runs)
        home_value = float(home_runs)
    except (TypeError, ValueError):
        return None

    if away_value > home_value:
        return "away"
    if home_value > away_value:
        return "home"
    return None


def _spread_covering_side(game_data: dict[str, Any]) -> str | None:
    score = game_data.get("score") or {}
    odds = game_data.get("odds") or {}
    away_runs = (score.get("away") or {}).get("runs")
    home_runs = (score.get("home") or {}).get("runs")
    away_line = ((odds.get("spread") or {}).get("away") or {}).get("line")
    home_line = ((odds.get("spread") or {}).get("home") or {}).get("line")
    if any(value is None for value in (away_runs, home_runs, away_line, home_line)):
        return None

    try:
        away_runs_value = float(away_runs)
        home_runs_value = float(home_runs)
        away_line_value = float(away_line)
        home_line_value = float(home_line)
    except (TypeError, ValueError):
        return None

    away_covers = away_runs_value + away_line_value > home_runs_value
    home_covers = home_runs_value + home_line_value > away_runs_value
    if away_covers == home_covers:
        return None
    return "away" if away_covers else "home"


def _total_runs_difference(game_data: dict[str, Any]) -> Decimal | None:
    score = game_data.get("score") or {}
    odds = game_data.get("odds") or {}
    away_runs = (score.get("away") or {}).get("runs")
    home_runs = (score.get("home") or {}).get("runs")
    total_line = ((odds.get("total_runs") or {}).get("line"))
    if any(value is None or value == "" for value in (away_runs, home_runs, total_line)):
        return None

    try:
        difference = Decimal(str(away_runs)) + Decimal(str(home_runs)) - Decimal(str(total_line))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return difference if difference.is_finite() else None


def _total_runs_covering_side(difference: Decimal | None) -> str | None:
    if difference is None:
        return None
    if difference > 0:
        return "over"
    if difference < 0:
        return "under"
    return "runs"


def _total_runs_difference_text(difference: Decimal | None, side: str) -> str:
    if difference is None or difference == 0:
        return ""
    if side == "over" and difference > 0:
        value = f"+{format(difference.normalize(), 'f')}"
    elif side == "under" and difference < 0:
        value = format(difference.normalize(), "f")
    else:
        return ""
    return f' <span class="total-runs-difference">({value})</span>'


def _has_odds_data(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_odds_data(item) for key, item in value.items() if key != "trend")
    if isinstance(value, list):
        return any(_has_odds_data(item) for item in value)
    if isinstance(value, str):
        return value.strip().upper() not in ("", "TBD")
    return value is not None


def _render_row(
    game_number: int,
    game_data: dict[str, Any],
    matchup_label: str,
    away_heading: str,
    home_heading: str,
    include_team_headers: bool,
) -> str:
    team_header_html = f'<thead><tr><th>{away_heading}</th><th>{home_heading}</th></tr></thead>' if include_team_headers else ""
    total_header_html = '<thead><tr><th>Under</th><th>Runs</th><th>Over</th></tr></thead>' if include_team_headers else ""

    odds = game_data["odds"]
    game_date, game_time = _safe_parse_start_time(game_data.get("start_time"))
    moneyline_away = odds["moneyline"]["away"]["trend"]
    moneyline_home = odds["moneyline"]["home"]["trend"]
    moneyline_away_score = _score_markup(game_data, "away")
    moneyline_home_score = _score_markup(game_data, "home")
    score_leader = _score_leader(game_data)
    away_score_class = ' class="moneyline-score-leader"' if score_leader == "away" else ""
    home_score_class = ' class="moneyline-score-leader"' if score_leader == "home" else ""
    spread_away = odds["spread"]["away"]["trend"]
    spread_home = odds["spread"]["home"]["trend"]
    spread_away_line = odds["spread"]["away"].get("line")
    spread_home_line = odds["spread"]["home"].get("line")
    spread_cover = _spread_covering_side(game_data)
    away_spread_class = ' class="spread-cover"' if spread_cover == "away" else ""
    home_spread_class = ' class="spread-cover"' if spread_cover == "home" else ""
    total_line = _normalize_total_line(odds["total_runs"].get("line"))
    total_difference = _total_runs_difference(game_data)
    total_cover = _total_runs_covering_side(total_difference)
    under_cover_class = ' class="total-runs-cover"' if total_cover == "under" else ""
    runs_cover_class = ' class="total-runs-cover"' if total_cover == "runs" else ""
    over_cover_class = ' class="total-runs-cover"' if total_cover == "over" else ""
    under_difference = _total_runs_difference_text(total_difference, "under")
    over_difference = _total_runs_difference_text(total_difference, "over")

    moneyline_table = (
        f'<table class="subtable" aria-label="{matchup_label} game {game_number} moneyline">'
        f'{team_header_html}'
        '<tbody><tr>'
        f'<td{away_score_class}><div class="moneyline-value-row"><span class="{_trend_class(moneyline_away)}">{moneyline_away}</span>{moneyline_away_score}</div><span class="location-value">Away</span></td>'
        f'<td{home_score_class}><div class="moneyline-value-row"><span class="{_trend_class(moneyline_home)}">{moneyline_home}</span>{moneyline_home_score}</div><span class="location-value">Home</span></td>'
        '</tr></tbody></table>'
    )
    spread_table = (
        f'<table class="subtable" aria-label="{matchup_label} game {game_number} spread">'
        f'{team_header_html}'
        '<tbody><tr>'
        f'<td{away_spread_class}><span class="{_trend_class(spread_away)}">{spread_away}{_spread_line_suffix(spread_away, spread_away_line)}</span><span class="location-value">Away</span></td>'
        f'<td{home_spread_class}><span class="{_trend_class(spread_home)}">{spread_home}{_spread_line_suffix(spread_home, spread_home_line)}</span><span class="location-value">Home</span></td>'
        '</tr></tbody></table>'
    )
    total_value_class = "trend-value tbd" if total_line == "TBD" else "trend-value"
    total_table = (
        f'<table class="subtable" aria-label="{matchup_label} game {game_number} total-runs">'
        f'{total_header_html}'
        '<tbody><tr>'
        f'<td{under_cover_class}><span class="trend-value ou-muted">Under{under_difference}</span></td>'
        f'<td{runs_cover_class}><span class="{total_value_class}">{total_line}</span></td>'
        f'<td{over_cover_class}><span class="trend-value ou-muted">Over{over_difference}</span></td>'
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

    rows: list[str] = []
    for game_number in (1, 2, 3):
        game_data = series_games.get(game_number)
        if game_data is None or not _has_odds_data(game_data.get("odds")):
            continue
        rows.append(
            _render_row(
                game_number,
                game_data,
                matchup_label,
                away_full,
                home_full,
                include_team_headers=not rows,
            )
        )

    if not rows:
        return ""

    joined_rows = "\n".join(rows)

    return (
        f'<section class="game" aria-labelledby="{section_id}">\n'
        '    <div class="top">\n'
        f'        <h2 id="{section_id}">{matchup_label}</h2>\n'
        '    </div>\n'
        '    <table>\n'
        f'        {header_cols}\n'
        '        <tbody>\n'
        f'        {joined_rows}\n'
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
        section_html = _render_game_block(f"g{index}", grouped[series_id])
        if section_html:
            sections.append(section_html)

    joined_sections = "\n\n    ".join(sections)
    report_type = "Wild Card Series"

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>{report_type} &mdash; {report_date_long}</title>
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
    <link href=\"https://fonts.googleapis.com/css2?family=Lexend:wght@400;500&display=swap\" rel=\"stylesheet\">
    <style>
        :root {{
            color-scheme: light;
            --h9s-black: #111111;
            --h9s-white: #FFFFFF;
            --h9s-green-dark: #0A5C36;
            --surface: rgba(17, 17, 17, 0.025);
            --border: rgba(17, 17, 17, 0.14);
            --muted: rgba(17, 17, 17, 0.62);
            font-family: 'Lexend', system-ui, -apple-system, 'Segoe UI', sans-serif;
            color: var(--h9s-black);
            background: var(--h9s-white);
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; padding: 30px; background: var(--h9s-white); }}
        main {{ max-width: 980px; margin: 0 auto; }}
        header {{ margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }}
        h1 {{ margin: 0 0 6px; font-size: 15px; font-weight: 500; letter-spacing: .03em; text-transform: uppercase; color: var(--h9s-black); }}
        .report-header-row {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; }}
        .report-title-group {{ display: flex; flex-direction: column; }}
        .report-subtitle {{ margin: 0; font-size: 15px; color: var(--h9s-green-dark); font-weight: 500; text-transform: uppercase; letter-spacing: .03em; }}
        .brand-logo {{ display: block; width: 100%; max-width: 260px; height: auto; margin: 0 auto 8px; padding: 8px; border-radius: 8px; background: var(--h9s-white); }}
        .brand-subtitle {{ margin: 0 0 4px; font-size: 28px; font-weight: 500; color: var(--h9s-black); }}
        .sub {{ margin: 0; color: var(--muted); font-size: 14px; white-space: nowrap; font-weight: 500; }}
        .game {{ margin: 0 0 14px; padding: 16px; background: var(--h9s-white); border: 1px solid var(--border); border-radius: 10px; break-inside: avoid; }}
        .top {{ display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }}
        h2 {{ margin: 0; font-size: 18px; font-weight: 500; color: var(--h9s-black); }}
        table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }}
        th, td {{ padding: 8px 7px; text-align: left; border-bottom: 1px solid var(--border); vertical-align: top; }}
        th {{ background: var(--surface); color: var(--h9s-green-dark); font-weight: 500; text-transform: uppercase; font-size: 11px; letter-spacing: .04em; }}
        .game > table th:nth-child(1) {{ width: 17.5%; }}
        .game > table th:nth-child(2), .game > table th:nth-child(3), .game > table th:nth-child(4) {{ width: 27.5%; }}
        .game > table th.col-spread, .game > table th.col-total-runs {{ background: var(--surface); color: var(--h9s-green-dark); text-transform: uppercase; font-size: 11px; letter-spacing: .04em; }}
        tr:last-child td {{ border-bottom: 0; }}
        .team {{ font-weight: 500; }}
        .game-number-cell {{ vertical-align: middle; padding-top: 10px; white-space: nowrap; }}
        .game-number {{ display: inline-block; color: var(--h9s-green-dark); font-weight: 500; margin-right: 8px; vertical-align: top; }}
        .game-date, .game-time {{ display: block; font-size: 11px; color: var(--muted); white-space: nowrap; }}
        .game-meta {{ display: inline-block; vertical-align: top; }}
        .subtable-cell {{ padding: 6px 7px; }}
        .subtable {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12px; }}
        .subtable th, .subtable td {{ padding: 4px 6px; border: 1px solid var(--border); background: transparent; text-align: left; }}
        .subtable tr > *:first-child:nth-last-child(2), .subtable tr > *:first-child:nth-last-child(2) ~ * {{ width: 50%; }}
        .subtable tr > *:first-child:nth-last-child(3), .subtable tr > *:first-child:nth-last-child(3) ~ * {{ width: 33.333%; }}
        .trend-value {{ display: block; font-weight: 400; color: var(--h9s-black); line-height: 1.1; }}
        .trend-value.favorite {{ font-weight: 700; }}
        .trend-value.tbd, .trend-value.ou-muted {{ color: rgba(17, 17, 17, 0.4); font-weight: 400; }}
        .spread-line {{ font-weight: 400; }}
        .moneyline-value-row {{ display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }}
        .moneyline-value-row .trend-value {{ display: inline; }}
        .score-value {{ margin-left: auto; color: var(--h9s-black); font-size: 16px; font-weight: 500; text-align: right; white-space: nowrap; }}
        .subtable td.moneyline-score-leader, .subtable td.spread-cover, .subtable td.total-runs-cover {{ background: rgba(10, 92, 54, 0.12); box-shadow: inset 0 0 0 1px var(--h9s-green-dark); }}
        .subtable td.total-runs-cover .ou-muted {{ color: var(--h9s-black); font-weight: 700; }}
        .total-runs-difference {{ font-weight: 400; }}
        .location-value {{ display: block; margin-top: 1px; font-size: 11px; color: var(--muted); line-height: 1.1; }}
        @media print {{
            body {{ padding: 0; }}
            main {{ max-width: none; }}
        }}
    </style>
</head>
<body>
<main>
    <header>
        <img class=\"brand-logo\" src=\"../assets/hard9stats-logo.png\" alt=\"Hard9Stats\">
        <p class=\"brand-subtitle\">MLB Playoffs 2026</p>
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
