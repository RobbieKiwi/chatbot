"""Read-side shapes of memory, free of SQLModel so the hook can use them."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from memorylayers.models.dates import Bucket
from memorylayers.models.vocab import SearchKind, TagKind


class FactLine(BaseModel):
    id: int
    detail: str
    occurred: str  # label, e.g. "2026-07" or "timeless"
    relevance: int
    tags: list[str]
    superseded_by: int | None = None


class FactCandidate(BaseModel):
    id: int
    detail: str
    tags: list[str]


class FactSpan(BaseModel):
    """A fact's dates and tags: what decides which periods and tag summaries it feeds."""

    id: int
    start: date | None
    end: date | None
    tags: list[str]


class TagLine(BaseModel):
    name: str
    kind: TagKind
    description: str
    fact_count: int  # current facts only
    has_summary: bool


class TagVocabulary(BaseModel):
    kinds: dict[str, TagKind]
    aliases: dict[str, str]  # alias -> canonical name


class NewTag(BaseModel):
    name: str
    kind: TagKind
    description: str


class TagResolution(BaseModel):
    names: list[str]
    to_create: list[NewTag]
    errors: list[str]


class TagDates(BaseModel):
    first_recorded: datetime | None
    last_recorded: datetime | None
    latest_occurred: date | None


class SearchHit(BaseModel):
    kind: SearchKind
    key: str
    snippet: str


class RefreshStatus(BaseModel):
    facts_since_refresh: int
    fact_count: int
    calendar_week_start: date | None


class RefreshPlan(BaseModel):
    through_revision: int
    calendar_week_start: date
    tag_names: list[str]
    periods: list[Bucket]
    expired_periods: list[str]

    @property
    def is_empty(self) -> bool:
        return not (self.tag_names or self.periods or self.expired_periods)


class BriefSection(BaseModel):
    """One tag or period the summariser must refresh, with what it needs."""

    title: str
    facts: list[FactLine]
    existing_summary: str
    child_summaries: dict[str, str] = Field(default_factory=dict)
