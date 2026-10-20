import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path
from typing import Any

from app.services.odds_normalization import normalize_moneyline_trends


_SERIES_REPORT_TITLES = {
    "WCS": "Wild Card Series",
    "LDS": "League Division Series",
    "LCS": "League Championship Series",
    "WS": "World Series",
}


def _parse_start_time(value: str) -> tuple[str, str]:
    cleaned = value.replace(" ET", "").strip()
    try:
        parsed = datetime.strptime(cleaned, "%Y-%m-%d %I:%M %p")
        return parsed.strftime("%b %d, %Y"), parsed.strftime("%I:%M %p").lstrip("0")
    except ValueError:
        parsed = datetime.strptime(cleaned, "%Y-%m-%d")
        return parsed.strftime("%b %d, %Y"), ""


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


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


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


def _total_market_data(odds: dict[str, Any]) -> dict[str, Any]:
    total = odds.get("total")
    return total if isinstance(total, dict) else {}


def _total_runs_difference(game_data: dict[str, Any]) -> Decimal | None:
    score = game_data.get("score") or {}
    odds = game_data.get("odds") or {}
    away_runs = (score.get("away") or {}).get("runs")
    home_runs = (score.get("home") or {}).get("runs")
    total_line = _total_market_data(odds).get("line")
    away_value = _as_decimal(away_runs)
    home_value = _as_decimal(home_runs)
    line_value = _as_decimal(total_line)
    if away_value is None or home_value is None or line_value is None:
        return None
    return away_value + home_value - line_value


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


def _is_final_game(game_data: dict[str, Any]) -> bool:
    status = str(game_data.get("status") or "").strip().casefold()
    return status.startswith("final") or status in {"complete", "completed", "finished", "game over", "ended"}


def _final_score(game_data: dict[str, Any]) -> tuple[Decimal, Decimal] | None:
    if not _is_final_game(game_data):
        return None
    score = game_data.get("score") or {}
    away_runs = _as_decimal((score.get("away") or {}).get("runs"))
    home_runs = _as_decimal((score.get("home") or {}).get("runs"))
    if away_runs is None or home_runs is None:
        return None
    return away_runs, home_runs


def _moneyline_outcome(
    game_data: dict[str, Any], final_score: tuple[Decimal, Decimal] | None
) -> str | None:
    if final_score is None:
        return None
    moneyline = (game_data.get("odds") or {}).get("moneyline") or {}
    away_favorite = (moneyline.get("away") or {}).get("trend") == "Favorite"
    home_favorite = (moneyline.get("home") or {}).get("trend") == "Favorite"
    if away_favorite == home_favorite:
        return None
    away_runs, home_runs = final_score
    favorite_runs, underdog_runs = (away_runs, home_runs) if away_favorite else (home_runs, away_runs)
    if favorite_runs > underdog_runs:
        return "favorite"
    if favorite_runs < underdog_runs:
        return "underdog"
    return None


def _spread_favorite_outcome(
    game_data: dict[str, Any], final_score: tuple[Decimal, Decimal] | None
) -> str | None:
    if final_score is None:
        return None
    spread = (game_data.get("odds") or {}).get("spread") or {}
    away_favorite = (spread.get("away") or {}).get("trend") == "Favorite"
    home_favorite = (spread.get("home") or {}).get("trend") == "Favorite"
    if away_favorite == home_favorite:
        return None
    favorite_market = spread.get("away" if away_favorite else "home") or {}
    favorite_line = _as_decimal(favorite_market.get("line"))
    if favorite_line is None:
        return None
    away_runs, home_runs = final_score
    favorite_runs, underdog_runs = (away_runs, home_runs) if away_favorite else (home_runs, away_runs)
    margin = favorite_runs + favorite_line - underdog_runs
    if margin > 0:
        return "covers"
    if margin < 0:
        return "no_covers"
    return "pushes"


def _total_runs_outcome(
    game_data: dict[str, Any], final_score: tuple[Decimal, Decimal] | None
) -> str | None:
    if final_score is None:
        return None
    difference = _total_runs_difference(game_data)
    if difference is None:
        return None
    if difference > 0:
        return "overs"
    if difference < 0:
        return "unders"
    return "pushes"


def _summarize_betting(games: Any) -> dict[str, dict[str, int]]:
    summary = {
        "moneyline": {"favorite": 0, "underdog": 0},
        "spread": {"covers": 0, "no_covers": 0, "pushes": 0},
        "total_runs": {"overs": 0, "unders": 0, "pushes": 0},
    }
    outcomes = {
        "moneyline": _moneyline_outcome,
        "spread": _spread_favorite_outcome,
        "total_runs": _total_runs_outcome,
    }
    for game_data in games:
        odds = game_data.get("odds") or {}
        final_score = _final_score(game_data)
        for market_name, outcome_for in outcomes.items():
            market_data = (
                _total_market_data(odds)
                if market_name == "total_runs"
                else odds.get(market_name)
            )
            if not _has_odds_data(market_data):
                continue
            outcome = outcome_for(game_data, final_score)
            if outcome is not None:
                summary[market_name][outcome] += 1
    return summary


def _count_phrase(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _render_betting_summary(
    games: Any,
    heading: str,
    heading_level: int,
    include_explanation: bool = False,
) -> str:
    summary = _summarize_betting(games)
    heading_tag = f"h{heading_level}"
    explanation = (
        '<p class="betting-summary-note">Moneyline counts wins by the listed favorite versus the underdog. '
        'Spread counts covers, no covers, and pushes for the listed spread favorite. '
        'Total Runs compares combined final runs with the line to determine Over, Under, or a push. '
        'Only games with final scores are counted.</p>'
        if include_explanation
        else ""
    )
    moneyline = summary["moneyline"]
    spread = summary["spread"]
    total_runs = summary["total_runs"]
    return (
        f'<div class="betting-summary"><{heading_tag}>{heading}</{heading_tag}>'
        f'{explanation}'
        '<div class="betting-summary-grid">'
        '<div class="betting-summary-item"><h3>Moneyline</h3>'
        '<div class="betting-outcomes betting-outcomes-two">'
        '<div class="betting-outcome"><span class="betting-outcome-label">Favorite<br>cover</span>'
        f'<span class="betting-outcome-count">{moneyline["favorite"]}</span></div>'
        '<div class="betting-outcome"><span class="betting-outcome-label">Underdog<br>cover</span>'
        f'<span class="betting-outcome-count">{moneyline["underdog"]}</span></div>'
        '</div></div>'
        '<div class="betting-summary-item"><h3>Spread</h3>'
        '<div class="betting-outcomes betting-outcomes-three">'
        '<div class="betting-outcome"><span class="betting-outcome-label">Favorite<br>cover</span>'
        f'<span class="betting-outcome-count">{spread["covers"]}</span></div>'
        '<div class="betting-outcome"><span class="betting-outcome-label">Underdog<br>cover</span>'
        f'<span class="betting-outcome-count">{spread["no_covers"]}</span></div>'
        '<div class="betting-outcome"><span class="betting-outcome-label">Push</span>'
        f'<span class="betting-outcome-count">{spread["pushes"]}</span></div>'
        '</div></div>'
        '<div class="betting-summary-item"><h3>Total Runs</h3>'
        '<div class="betting-outcomes betting-outcomes-three">'
        '<div class="betting-outcome"><span class="betting-outcome-label">Under</span>'
        f'<span class="betting-outcome-count">{total_runs["unders"]}</span></div>'
        '<div class="betting-outcome"><span class="betting-outcome-label">Push</span>'
        f'<span class="betting-outcome-count">{total_runs["pushes"]}</span></div>'
        '<div class="betting-outcome"><span class="betting-outcome-label">Over</span>'
        f'<span class="betting-outcome-count">{total_runs["overs"]}</span></div>'
        '</div></div>'
        '</div></div>'
    )


def _render_row(
    game_number: int,
    game_data: dict[str, Any],
    matchup_label: str,
    first_team_heading: str,
    second_team_heading: str,
    column_sides: tuple[str, str],
    include_team_headers: bool,
) -> str:
    team_header_html = f'<thead><tr><th>{first_team_heading}</th><th>{second_team_heading}</th></tr></thead>' if include_team_headers else ""
    total_header_html = '<thead><tr><th>Under</th><th>Runs</th><th>Over</th></tr></thead>' if include_team_headers else ""

    odds = game_data["odds"]
    game_date, game_time = _safe_parse_start_time(game_data.get("start_time") or game_data.get("date"))
    score_leader = _score_leader(game_data)
    spread_cover = _spread_covering_side(game_data)
    moneyline_cells: list[str] = []
    spread_cells: list[str] = []
    for side in column_sides:
        moneyline_trend = odds["moneyline"][side]["trend"]
        moneyline_score = _score_markup(game_data, side)
        score_class = ' class="moneyline-score-leader"' if score_leader == side else ""
        location = "Away" if side == "away" else "Home"
        moneyline_cells.append(
            f'<td{score_class}><div class="moneyline-value-row"><span class="{_trend_class(moneyline_trend)}">{moneyline_trend}</span>{moneyline_score}</div><span class="location-value">{location}</span></td>'
        )

        spread_trend = odds["spread"][side]["trend"]
        spread_line = odds["spread"][side].get("line")
        spread_class = ' class="spread-cover"' if spread_cover == side else ""
        spread_cells.append(
            f'<td{spread_class}><span class="{_trend_class(spread_trend)}">{spread_trend}{_spread_line_suffix(spread_trend, spread_line)}</span><span class="location-value">{location}</span></td>'
        )

    total_line = _normalize_total_line(_total_market_data(odds).get("line"))
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
        f'{"".join(moneyline_cells)}'
        '</tr></tbody></table>'
    )
    spread_table = (
        f'<table class="subtable" aria-label="{matchup_label} game {game_number} spread">'
        f'{team_header_html}'
        '<tbody><tr>'
        f'{"".join(spread_cells)}'
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


def _series_group_key(game_data: dict[str, Any]) -> tuple[str, ...]:
    teams = game_data.get("teams") or {}
    team_names = []
    for side in ("away", "home"):
        team = teams.get(side) or {}
        abbreviation = team.get("abbr")
        if abbreviation and str(abbreviation).strip().casefold() != "tbd":
            name = abbreviation
        else:
            name = team.get("full_name") or team.get("name")
        if not name:
            team_names = []
            break
        team_names.append("".join(character for character in str(name).casefold() if character.isalnum()))

    if len(team_names) == 2:
        return ("teams", *sorted(team_names))

    series_id = str(game_data.get("series_id") or "").strip().casefold()
    if " at " in series_id:
        participants = [part.strip() for part in series_id.split(" at ", maxsplit=1)]
        return ("series_id", *sorted(participants))

    id_parts = series_id.split("_")
    if len(id_parts) >= 3:
        return ("series_id", "_".join(id_parts[:-2]), *sorted(id_parts[-2:]))
    return ("series_id", series_id)


def _team_identity(team: dict[str, Any]) -> str:
    abbreviation = team.get("abbr")
    if abbreviation and str(abbreviation).strip().casefold() != "tbd":
        name = abbreviation
    else:
        name = team.get("full_name") or team.get("name")
    return "".join(character for character in str(name or "").casefold() if character.isalnum())


def _render_game_block(section_id: str, series_games: dict[int, dict[str, Any]]) -> str:
    game_one = series_games.get(1) or next(iter(series_games.values()))
    game_one_teams = game_one.get("teams") or {}
    game_one_away = game_one_teams.get("away") or {}
    game_one_home = game_one_teams.get("home") or {}
    away_full = game_one_away.get("full_name") or game_one_away.get("name") or "Away"
    home_full = game_one_home.get("full_name") or game_one_home.get("name") or "Home"
    game_one_away_identity = _team_identity(game_one_away)
    matchup_label = f"{away_full} at {home_full}"

    header_cols = '<thead><tr><th class="col-game">Game</th><th class="col-moneyline">Moneyline</th><th class="col-spread">Spread</th><th class="col-total-runs">Total Runs</th></tr></thead>'

    rows: list[str] = []
    for game_number in sorted(series_games):
        game_data = series_games.get(game_number)
        if game_data is None or not _has_odds_data(game_data.get("odds")):
            continue
        game_teams = game_data.get("teams") or {}
        game_away = game_teams.get("away") or {}
        game_home = game_teams.get("home") or {}
        if _team_identity(game_away) == game_one_away_identity:
            column_sides = ("away", "home")
        elif _team_identity(game_home) == game_one_away_identity:
            column_sides = ("home", "away")
        else:
            column_sides = ("away", "home")
        rows.append(
            _render_row(
                game_number,
                game_data,
                matchup_label,
                away_full,
                home_full,
                column_sides,
                include_team_headers=not rows,
            )
        )

    if not rows:
        return ""

    joined_rows = "\n".join(rows)
    betting_summary = _render_betting_summary(series_games.values(), "Series Betting Totals", 3)

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
        f'    {betting_summary}\n'
        '</section>'
    )


def render_report_html(merged_payload: dict[str, Any]) -> str:
    normalize_moneyline_trends(merged_payload)
    report_date_value = merged_payload.get("generated_report_date") or datetime.now().astimezone().strftime("%Y-%m-%d")
    report_date = datetime.strptime(report_date_value, "%Y-%m-%d")
    report_date_long = report_date.strftime("%B %d, %Y")

    grouped: dict[tuple[str, ...], dict[int, dict[str, Any]]] = defaultdict(dict)
    ordered_series: list[tuple[str, ...]] = []
    for game in merged_payload["games"]:
        series_key = _series_group_key(game)
        if series_key not in grouped:
            ordered_series.append(series_key)
        grouped[series_key][int(game["game_number"])] = game

    sections: list[str] = []
    for index, series_key in enumerate(ordered_series, start=1):
        section_html = _render_game_block(f"g{index}", grouped[series_key])
        if section_html:
            sections.append(section_html)

    joined_sections = "\n\n    ".join(sections)
    overall_summary = _render_betting_summary(
        merged_payload["games"],
        "Overall Betting Totals",
        2,
    )
    series_type = str(merged_payload.get("series_type") or "WCS").strip().upper()
    report_type = _SERIES_REPORT_TITLES.get(series_type, _SERIES_REPORT_TITLES["WCS"])

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
        .betting-summary {{ margin-top: 14px; padding: 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }}
        main > .betting-summary {{ margin-bottom: 14px; }}
        .betting-summary > h2, .betting-summary > h3 {{ margin: 0 0 10px; font-size: 16px; font-weight: 500; color: var(--h9s-black); }}
        .betting-summary-note {{ margin: 0 0 10px; color: var(--muted); font-size: 12px; line-height: 1.4; }}
        .betting-summary-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
        .betting-summary-item {{ padding: 10px; background: var(--h9s-white); border: 1px solid var(--border); border-radius: 8px; break-inside: avoid; }}
        .betting-summary-item h3 {{ margin: 0 0 4px; color: var(--h9s-green-dark); font-size: 13px; font-weight: 500; }}
        .betting-summary-item p {{ margin: 0; color: var(--h9s-black); font-size: 12px; line-height: 1.4; }}
        .betting-outcomes {{ display: grid; border: 1px solid var(--border); border-radius: 7px; overflow: hidden; }}
        .betting-outcomes-two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .betting-outcomes-three {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
        .betting-outcome {{ display: flex; min-width: 0; min-height: 58px; flex-direction: column; align-items: center; justify-content: center; gap: 4px; padding: 7px 4px; text-align: center; }}
        .betting-outcome + .betting-outcome {{ border-left: 1px solid var(--border); }}
        .betting-outcome-label {{ color: var(--muted); font-size: 10px; font-weight: 500; letter-spacing: .03em; line-height: 1.2; text-transform: uppercase; }}
        .betting-outcome-count {{ color: var(--h9s-green-dark); font-size: 20px; font-weight: 500; line-height: 1; }}
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
        @media (max-width: 700px) {{
            .betting-summary-grid {{ grid-template-columns: 1fr; }}
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

    {overall_summary}

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
