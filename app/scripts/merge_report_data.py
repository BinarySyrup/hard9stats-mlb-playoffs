import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


TIME_FORMAT = "%Y-%m-%d %I:%M %p"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_team(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _team_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name", "")).strip()
    return str(value or "").strip()


def _split_team_name(full_name: str) -> tuple[str, str]:
    parts = full_name.split()
    if len(parts) > 1 and parts[0].isupper() and len(parts[0]) <= 4:
        return parts[0], " ".join(parts[1:])
    return (parts[0].upper()[:4] if parts else "TBD", full_name)


def _compute_trend(away_value: float, home_value: float) -> tuple[str, str]:
    if away_value < home_value:
        return "Favorite", "Underdog"
    return "Underdog", "Favorite"


def _extract_games(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("games"), list):
        return [game for game in data["games"] if isinstance(game, dict)]
    games = payload.get("games")
    if isinstance(games, list):
        return [game for game in games if isinstance(game, dict)]
    return []


def _build_score_lookup(scores_files: list[Path]) -> dict[tuple[str, str, int], dict[str, Any]]:
    lookup: dict[tuple[str, str, int], dict[str, Any]] = {}
    for score_file in sorted(scores_files):
        payload = _load_json(score_file)
        game_date = payload.get("date")
        for game in _extract_games(payload):
            away = _team_name(game.get("away_team"))
            home = _team_name(game.get("home_team"))
            game_number = int(game.get("series", {}).get("game", 1))
            lookup[(_norm_team(away), _norm_team(home), game_number)] = {
                "file": str(score_file).replace("\\", "/"),
                "date": game_date,
                "status": game.get("status", ""),
                "away": game.get("away_team", {}),
                "home": game.get("home_team", {}),
                "series": game.get("series", {}),
            }
    return lookup


def _build_schedule_rows(schedule_files: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for schedule_file in sorted(schedule_files):
        payload = _load_json(schedule_file)
        for game in _extract_games(payload):
            rows.append(
                {
                    "file": str(schedule_file).replace("\\", "/"),
                    "away": _team_name(game.get("away_team")),
                    "home": _team_name(game.get("home_team")),
                    "game_number": int(game.get("game_number", game.get("series", {}).get("game", 1))),
                    "series_id": game.get("series_id"),
                    "league": game.get("series", {}).get("league") or game.get("league"),
                    "start_time": game.get("start_time"),
                    "status": game.get("status"),
                    "venue": game.get("venue"),
                    "summary": game.get("series", {}).get("summary"),
                }
            )
    return rows


def _match_score(
    score_by_key: dict[tuple[str, str, int], dict[str, Any]],
    away_name: str,
    home_name: str,
    game_number: int,
) -> dict[str, Any] | None:
    away_norm = _norm_team(away_name)
    home_norm = _norm_team(home_name)
    for (away_score, home_score, score_game_number), value in score_by_key.items():
        away_match = away_norm.endswith(away_score) or away_score.endswith(away_norm)
        home_match = home_norm.endswith(home_score) or home_score.endswith(home_norm)
        if away_match and home_match and score_game_number == game_number:
            return value
    return None


def _team_signature(name: str) -> set[str]:
    norm = _norm_team(name)
    tokens = [token for token in re.split(r"[^a-z0-9]+", norm) if token]
    signature = set(tokens)

    if tokens:
        first = tokens[0]
        alias_map = {
            "phi": "philadelphia",
            "philadelphia": "phi",
            "ny": "newyork",
            "new": "ny",
            "newyork": "ny",
            "chi": "chicago",
            "chicago": "chi",
            "bos": "boston",
            "boston": "bos",
            "atl": "atlanta",
            "atlanta": "atl",
            "hou": "houston",
            "houston": "hou",
            "sd": "sandiego",
            "sandiego": "sd",
            "san": "sd",
        }
        alias = alias_map.get(first)
        if alias:
            signature.add(alias)

    joined = "".join(tokens)
    if joined:
        signature.add(joined)

    return signature


def _matches_team(schedule_name: str, known_name: str) -> bool:
    sched = _team_signature(schedule_name)
    known = _team_signature(known_name)
    return bool(sched & known)


def _league_family(value: str | None) -> str | None:
    if not value:
        return None
    upper = value.upper()
    if upper.startswith("AL") or upper.startswith("AMERICAN"):
        return "AL"
    if upper.startswith("NL") or upper.startswith("NATIONAL"):
        return "NL"
    return None


def _infer_series_id_from_schedule(
    schedule_row: dict[str, Any],
    known_series: dict[str, dict[str, Any]],
) -> str | None:
    away = schedule_row["away"]
    home = schedule_row["home"]
    sched_league = _league_family(schedule_row.get("league"))

    candidates: list[str] = []
    for series_id, info in known_series.items():
        if not _matches_team(away, info["away_full"]):
            continue
        if not _matches_team(home, info["home_full"]):
            continue
        known_league = _league_family(str(info.get("league") or ""))
        if sched_league and known_league and sched_league != known_league:
            continue
        candidates.append(series_id)

    if len(candidates) == 1:
        return candidates[0]
    return candidates[0] if candidates else None


def _resolve_odds_game_number(
    game: dict[str, Any],
    series_id: str,
    away_full: str,
    home_full: str,
    schedule_rows: list[dict[str, Any]],
    by_series_game: dict[tuple[str, int], dict[str, Any]],
) -> int:
    game_number = game.get("game_number")
    if game_number is None:
        game_number = game.get("series", {}).get("game")
    if game_number is not None:
        return int(game_number)

    scheduled_numbers = {
        int(row["game_number"])
        for row in schedule_rows
        if row.get("game_number") is not None
        and (not row.get("series_id") or str(row["series_id"]) == series_id)
        and _matches_team(row["away"], away_full)
        and _matches_team(row["home"], home_full)
    }
    existing_numbers = {number for existing_series, number in by_series_game if existing_series == series_id}
    remaining_numbers = scheduled_numbers - existing_numbers
    if len(remaining_numbers) == 1:
        return remaining_numbers.pop()

    raise ValueError(f"Unable to determine game number for {away_full} at {home_full} in {series_id}.")


def _build_tbd_merged_row(
    series_id: str,
    game_number: int,
    away_full: str,
    home_full: str,
    league: str | None,
    schedule_row: dict[str, Any] | None,
) -> dict[str, Any]:
    away_abbr, away_short = _split_team_name(away_full)
    home_abbr, home_short = _split_team_name(home_full)

    return {
        "series_id": series_id,
        "league": league,
        "game_number": game_number,
        "start_time": schedule_row.get("start_time") if schedule_row else None,
        "status": (schedule_row.get("status") if schedule_row else None) or "Scheduled",
        "matchup": {"away": away_full, "home": home_full},
        "teams": {
            "away": {
                "abbr": away_abbr,
                "name": away_short,
                "full_name": away_full,
                "pitcher": None,
                "record": None,
                "split_record": None,
            },
            "home": {
                "abbr": home_abbr,
                "name": home_short,
                "full_name": home_full,
                "pitcher": None,
                "record": None,
                "split_record": None,
            },
        },
        "odds": {
            "moneyline": {
                "away": {"value": None, "trend": "TBD"},
                "home": {"value": None, "trend": "TBD"},
            },
            "spread": {
                "away": {"line": None, "odds": None, "trend": "TBD"},
                "home": {"line": None, "odds": None, "trend": "TBD"},
            },
            "total_runs": {
                "line": None,
                "over_odds": None,
                "under_odds": None,
            },
        },
        "score": {
            "away": {"runs": None, "hits": None, "errors": None},
            "home": {"runs": None, "hits": None, "errors": None},
        },
        "schedule": {
            "venue": schedule_row.get("venue") if schedule_row else None,
        },
        "series": {
            "summary": schedule_row.get("summary") if schedule_row else None,
        },
        "sources": {
            "odds": None,
            "score": None,
            "schedule": schedule_row.get("file") if schedule_row else None,
        },
    }


def _parse_start_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace(" ET", "").strip()
    try:
        return datetime.strptime(text, TIME_FORMAT)
    except ValueError:
        return None


def _format_start_time(value: datetime) -> str:
    return f"{value.strftime(TIME_FORMAT)} ET"


def _infer_missing_start_times(by_series_game: dict[tuple[str, int], dict[str, Any]]) -> None:
    series_ids = sorted({key[0] for key in by_series_game.keys()})
    for series_id in series_ids:
        rows: list[dict[str, Any]] = [
            by_series_game[(series_id, game_number)]
            for _, game_number in sorted(
                [key for key in by_series_game.keys() if key[0] == series_id], key=lambda item: item[1]
            )
        ]

        known_times: dict[int, datetime] = {}
        for row in rows:
            game_number = int(row["game_number"])
            parsed = _parse_start_time(row.get("start_time"))
            if parsed is not None:
                known_times[game_number] = parsed

        if not known_times:
            continue

        for row in rows:
            game_number = int(row["game_number"])
            if row.get("start_time"):
                continue

            lower_known = [num for num in known_times.keys() if num < game_number]
            upper_known = [num for num in known_times.keys() if num > game_number]

            inferred: datetime | None = None
            if lower_known:
                anchor = max(lower_known)
                inferred = known_times[anchor] + timedelta(days=(game_number - anchor))
            elif upper_known:
                anchor = min(upper_known)
                inferred = known_times[anchor] - timedelta(days=(anchor - game_number))

            if inferred is not None:
                row["start_time"] = _format_start_time(inferred)


def merge_report_data(odds_dir: Path, scores_dir: Path, schedules_dir: Path | None = None) -> dict[str, Any]:
    odds_files = sorted(odds_dir.glob("*.json"))
    scores_files = sorted(scores_dir.glob("*.json"))
    schedule_files = sorted(schedules_dir.glob("*.json")) if schedules_dir and schedules_dir.exists() else []

    score_by_key = _build_score_lookup(scores_files)
    schedule_rows = _build_schedule_rows(schedule_files)

    by_series_game: dict[tuple[str, int], dict[str, Any]] = {}
    known_series: dict[str, dict[str, Any]] = {}

    for odds_file in odds_files:
        payload = _load_json(odds_file)
        for game in _extract_games(payload):
            series_id = str(game.get("series_id", "UNKNOWN_SERIES"))
            away_full = _team_name(game.get("away_team"))
            home_full = _team_name(game.get("home_team"))
            game_number = _resolve_odds_game_number(
                game=game,
                series_id=series_id,
                away_full=away_full,
                home_full=home_full,
                schedule_rows=schedule_rows,
                by_series_game=by_series_game,
            )
            away_abbr, away_short = _split_team_name(away_full)
            home_abbr, home_short = _split_team_name(home_full)

            known_series[series_id] = {
                "away_full": away_full,
                "home_full": home_full,
                "league": game.get("league"),
            }

            score = _match_score(score_by_key, away_full, home_full, game_number)

            away_moneyline = int(game["odds"]["away"]["moneyline"])
            home_moneyline = int(game["odds"]["home"]["moneyline"])
            away_ml_trend, home_ml_trend = _compute_trend(away_moneyline, home_moneyline)

            away_spread = float(game["odds"]["away"]["run_line"]["line"])
            home_spread = float(game["odds"]["home"]["run_line"]["line"])
            away_spread_trend, home_spread_trend = _compute_trend(away_spread, home_spread)

            merged = {
                "series_id": series_id,
                "league": game.get("league"),
                "game_number": game_number,
                "start_time": game.get("start_time"),
                "status": score.get("status") if score and score.get("status") else "Scheduled",
                "matchup": {"away": away_full, "home": home_full},
                "teams": {
                    "away": {
                        "abbr": away_abbr,
                        "name": away_short,
                        "full_name": away_full,
                        "pitcher": game.get("away_team", {}).get("pitcher"),
                        "record": score.get("away", {}).get("record") if score else None,
                        "split_record": score.get("away", {}).get("split_record") if score else None,
                    },
                    "home": {
                        "abbr": home_abbr,
                        "name": home_short,
                        "full_name": home_full,
                        "pitcher": game.get("home_team", {}).get("pitcher"),
                        "record": score.get("home", {}).get("record") if score else None,
                        "split_record": score.get("home", {}).get("split_record") if score else None,
                    },
                },
                "odds": {
                    "moneyline": {
                        "away": {"value": away_moneyline, "trend": away_ml_trend},
                        "home": {"value": home_moneyline, "trend": home_ml_trend},
                    },
                    "spread": {
                        "away": {
                            "line": away_spread,
                            "odds": int(game["odds"]["away"]["run_line"]["odds"]),
                            "trend": away_spread_trend,
                        },
                        "home": {
                            "line": home_spread,
                            "odds": int(game["odds"]["home"]["run_line"]["odds"]),
                            "trend": home_spread_trend,
                        },
                    },
                    "total_runs": {
                        "line": game["odds"]["away"]["total"].get("line"),
                        "over_odds": game["odds"]["away"]["total"].get("over_odds"),
                        "under_odds": game["odds"]["home"]["total"].get("under_odds"),
                    },
                },
                "score": {
                    "away": {
                        "runs": score.get("away", {}).get("runs") if score else None,
                        "hits": score.get("away", {}).get("hits") if score else None,
                        "errors": score.get("away", {}).get("errors") if score else None,
                    },
                    "home": {
                        "runs": score.get("home", {}).get("runs") if score else None,
                        "hits": score.get("home", {}).get("hits") if score else None,
                        "errors": score.get("home", {}).get("errors") if score else None,
                    },
                },
                "schedule": {
                    "venue": None,
                },
                "series": {
                    "summary": score.get("series", {}).get("summary") if score else None,
                },
                "sources": {
                    "odds": str(odds_file).replace("\\", "/"),
                    "score": score.get("file") if score else None,
                    "schedule": None,
                },
            }

            by_series_game[(series_id, game_number)] = merged

    for schedule_row in schedule_rows:
        schedule_series_id = schedule_row.get("series_id")
        if schedule_series_id:
            series_id = str(schedule_series_id)
        else:
            series_id = _infer_series_id_from_schedule(schedule_row, known_series)

        if not series_id:
            continue

        key = (series_id, int(schedule_row["game_number"]))
        existing = by_series_game.get(key)

        if existing is None:
            base = known_series.get(series_id)
            away_full = base["away_full"] if base else schedule_row["away"]
            home_full = base["home_full"] if base else schedule_row["home"]
            league = base.get("league") if base else None

            by_series_game[key] = _build_tbd_merged_row(
                series_id=series_id,
                game_number=int(schedule_row["game_number"]),
                away_full=away_full,
                home_full=home_full,
                league=league,
                schedule_row=schedule_row,
            )
            continue

        if not existing.get("start_time") and schedule_row.get("start_time"):
            existing["start_time"] = schedule_row.get("start_time")
        if existing.get("status") in (None, "", "Scheduled") and schedule_row.get("status"):
            existing["status"] = schedule_row.get("status")
        if existing.get("schedule", {}).get("venue") is None and schedule_row.get("venue") is not None:
            existing.setdefault("schedule", {})["venue"] = schedule_row.get("venue")
        if existing.get("series", {}).get("summary") is None and schedule_row.get("summary"):
            existing.setdefault("series", {})["summary"] = schedule_row.get("summary")
        if existing.get("sources", {}).get("schedule") is None:
            existing.setdefault("sources", {})["schedule"] = schedule_row.get("file")

    _infer_missing_start_times(by_series_game)

    games = [
        by_series_game[key]
        for key in sorted(by_series_game.keys(), key=lambda item: (item[0], item[1]))
    ]

    report_date = max(
        (str(game["start_time"])[:10] for game in games if game.get("start_time")),
        default=datetime.now().strftime("%Y-%m-%d"),
    )

    source_files: dict[str, Any] = {
        "odds": [str(path).replace("\\", "/") for path in odds_files],
        "scores": [str(path).replace("\\", "/") for path in scores_files],
    }
    if schedule_files:
        source_files["schedules"] = [str(path).replace("\\", "/") for path in schedule_files]

    return {
        "report_date": report_date,
        "report_type": "Game Report - Wild Card",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_files": source_files,
        "games": games,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge all odds and scores JSON (and optional schedules JSON) into a single report JSON file."
    )
    parser.add_argument(
        "--odds-dir",
        default="data/ingested/WCS/odds",
        help="Directory containing odds JSON files.",
    )
    parser.add_argument(
        "--scores-dir",
        default="data/ingested/WCS/scores",
        help="Directory containing score JSON files.",
    )
    parser.add_argument(
        "--schedules-dir",
        default="data/ingested/WCS/schedules",
        help="Optional directory containing schedule JSON files.",
    )
    parser.add_argument(
        "--output",
        default="data/reports/WCS/report-merged.json",
        help="Output merged report JSON file path.",
    )
    args = parser.parse_args()

    schedules_dir = Path(args.schedules_dir)
    payload = merge_report_data(
        odds_dir=Path(args.odds_dir),
        scores_dir=Path(args.scores_dir),
        schedules_dir=schedules_dir if schedules_dir.exists() else None,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Generated {output_path} with {len(payload['games'])} games")


if __name__ == "__main__":
    main()
