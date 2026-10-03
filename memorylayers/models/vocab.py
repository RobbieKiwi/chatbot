"""Closed vocabularies shared across memorylayers."""

from enum import StrEnum


class Precision(StrEnum):
    """How precisely a fact's occurred range is known."""

    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    DECADE = "decade"
    UNKNOWN = "unknown"  # an event whose date is not known
    TIMELESS = "timeless"  # a standing trait; belongs to no period


class TagKind(StrEnum):
    CATEGORY = "category"  # closed vocabulary
    ENTITY = "entity"  # people, places, organisations; open


class PeriodKind(StrEnum):
    ERA = "era"
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"
    WEEK = "week"


class SearchKind(StrEnum):
    FACT = "fact"
    TAG = "tag"
    TAG_SUMMARY = "tag_summary"
    PERIOD = "period"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class WorkerKind(StrEnum):
    SCRIBE = "scribe"
    SUMMARISER = "summariser"
    CONSOLIDATOR = "consolidator"
    MIGRATOR = "migrator"


SPECIAL_CATEGORIES = ("core", "agent_preferences")
