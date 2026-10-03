"""Simple date mentions in a message, as candidate period names for memory hints."""

import re
from datetime import date, timedelta

from memorylayers.tools.calendar import quarter_of, week_bucket, week_start

# "may" is left out: as a word it is far more often a verb.
_MONTHS = {name: number for number, name in enumerate(["january", "february", "march", "april", "", "june", "july", "august", "september", "october", "november", "december"], start=1) if name}
_SEASON_QUARTERS = {"winter": 1, "spring": 2, "summer": 3, "autumn": 4, "fall": 4}


def _month_names(*, year: int, month: int) -> list[str]:
    return [f"{year}-{month:02d}", f"{year} Q{quarter_of(month=month)}", str(year)]


def period_names_mentioned(*, text: str, today: date) -> list[list[str]]:
    lowered = text.lower()
    mentions: list[tuple[int, list[str]]] = []
    for match in re.finditer(r"\b(19\d{2}|20\d{2})\b", lowered):
        mentions.append((match.start(), [match[1]]))
    for match in re.finditer(r"\b(" + "|".join(_MONTHS) + r")\b", lowered):
        month = _MONTHS[match[1]]
        year = today.year if month <= today.month else today.year - 1
        mentions.append((match.start(), _month_names(year=year, month=month)))
    for match in re.finditer(r"\b(?:(last|this)\s+)?(" + "|".join(_SEASON_QUARTERS) + r")\b", lowered):
        quarter = _SEASON_QUARTERS[match[2]]
        current = quarter_of(month=today.month)
        year = today.year if match[1] == "this" or quarter < current else today.year - 1
        mentions.append((match.start(), [f"{year} Q{quarter}", str(year)]))
    for match in re.finditer(r"\b(last|this)\s+(week|month|year)\b", lowered):
        mentions.append((match.start(), _relative(which=match[1], unit=match[2], today=today)))
    return [names for _, names in sorted(mentions, key=lambda mention: mention[0])]


def _relative(*, which: str, unit: str, today: date) -> list[str]:
    if unit == "year":
        return [str(today.year - (which == "last"))]
    if unit == "month":
        first = today.replace(day=1)
        day = first - timedelta(days=1) if which == "last" else first
        return _month_names(year=day.year, month=day.month)
    start = week_start(day=today) - timedelta(days=7 if which == "last" else 0)
    return [week_bucket(start=start).name, *_month_names(year=start.year, month=start.month)]
