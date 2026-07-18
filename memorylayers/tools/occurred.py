"""The --occurred values writers pass, and labels for stored ranges."""

import calendar
import re
from datetime import date

from memorylayers.models.dates import ONGOING_END, OccurredRange
from memorylayers.models.vocab import Precision

_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")
_YEAR = re.compile(r"^(\d{4})$")
_DECADE = re.compile(r"^(\d{3})0s$")
_COARSENESS = [Precision.DAY, Precision.MONTH, Precision.YEAR, Precision.DECADE]
_FORMATS = "use YYYY-MM-DD, YYYY-MM, YYYY, YYYYs (a decade), A..B, unknown, or --timeless"

TIMELESS = OccurredRange(start=None, end=None, precision=Precision.TIMELESS)


class OccurredFormatError(ValueError):
    pass


def _parse_single(*, text: str) -> tuple[date, date, Precision]:
    try:
        if match := _DAY.match(text):
            day = date(int(match[1]), int(match[2]), int(match[3]))
            return day, day, Precision.DAY
        if match := _MONTH.match(text):
            year, month = int(match[1]), int(match[2])
            last = calendar.monthrange(year, month)[1]
            return date(year, month, 1), date(year, month, last), Precision.MONTH
        if match := _YEAR.match(text):
            year = int(match[1])
            return date(year, 1, 1), date(year, 12, 31), Precision.YEAR
        if match := _DECADE.match(text):
            year = int(match[1]) * 10
            return date(year, 1, 1), date(year + 9, 12, 31), Precision.DECADE
    except ValueError as error:
        raise OccurredFormatError(f"cannot read {text!r}: {error}") from error
    raise OccurredFormatError(f"cannot read {text!r}: {_FORMATS}")


def parse_occurred(*, text: str) -> OccurredRange:
    text = text.strip()
    if text == "unknown":
        return OccurredRange(start=None, end=None, precision=Precision.UNKNOWN)
    if ".." in text:
        first, last = text.split("..", 1)
        start, _, first_precision = _parse_single(text=first)
        _, end, last_precision = _parse_single(text=last)
        if end < start:
            raise OccurredFormatError(f"range {text!r} ends before it starts")
        precision = max(first_precision, last_precision, key=_COARSENESS.index)
        return OccurredRange(start=start, end=end, precision=precision)
    start, end, precision = _parse_single(text=text)
    return OccurredRange(start=start, end=end, precision=precision)


def _label_date(*, day: date, precision: Precision) -> str:
    match precision:
        case Precision.DAY:
            return day.isoformat()
        case Precision.MONTH:
            return f"{day.year}-{day.month:02d}"
        case Precision.YEAR:
            return str(day.year)
        case _:
            return f"{day.year // 10 * 10}s"


def label_occurred(*, occurred: OccurredRange) -> str:
    if occurred.precision is Precision.TIMELESS:
        return "timeless"
    if occurred.start is None or occurred.end is None:
        return "date unknown"
    first = _label_date(day=occurred.start, precision=occurred.precision)
    if occurred.end == ONGOING_END:
        return f"{first}..ongoing"
    last = _label_date(day=occurred.end, precision=occurred.precision)
    return first if first == last else f"{first}..{last}"
