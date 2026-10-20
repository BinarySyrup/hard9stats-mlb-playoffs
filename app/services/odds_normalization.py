from decimal import Decimal, InvalidOperation
from typing import Any


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value).strip().replace("−", "-"))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _normalize_moneyline_pair(away: Any, home: Any) -> None:
    if not isinstance(away, dict) or not isinstance(home, dict):
        return

    away_odds = _as_decimal(away.get("odds"))
    home_odds = _as_decimal(home.get("odds"))
    if away_odds is None or home_odds is None or away_odds == home_odds:
        away["trend"] = "TBD"
        home["trend"] = "TBD"
    elif away_odds < home_odds:
        away["trend"] = "Favorite"
        home["trend"] = "Underdog"
    else:
        away["trend"] = "Underdog"
        home["trend"] = "Favorite"


def normalize_moneyline_trends(payload: Any) -> None:
    """Set Moneyline trends from signed odds in extraction and merged JSON."""
    if isinstance(payload, list):
        for item in payload:
            normalize_moneyline_trends(item)
        return
    if not isinstance(payload, dict):
        return

    odds = payload.get("odds")
    if isinstance(odds, dict):
        moneyline = odds.get("moneyline")
        if isinstance(moneyline, dict):
            _normalize_moneyline_pair(moneyline.get("away"), moneyline.get("home"))
        else:
            away = odds.get("away")
            home = odds.get("home")
            if isinstance(away, dict) and isinstance(home, dict):
                _normalize_moneyline_pair(away.get("moneyline"), home.get("moneyline"))

    for value in payload.values():
        normalize_moneyline_trends(value)
