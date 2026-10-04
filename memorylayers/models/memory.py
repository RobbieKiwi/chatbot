"""The memory database. Datetimes are timezone-aware UTC; dates are local calendar dates."""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel

from memorylayers.models.tables import FACT_TABLE, FACT_TAG_TABLE, GAP_TABLE, PERIOD_TABLE, REFRESH_STATE_TABLE, TAG_ALIAS_TABLE, TAG_SUMMARY_TABLE, TAG_TABLE
from memorylayers.models.vocab import PeriodKind, Precision, TagKind


class UtcDateTime(TypeDecorator[datetime]):
    """A timezone-aware datetime stored as UTC ISO text."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime; memory stores timezone-aware UTC")
        return value.astimezone(UTC).isoformat()

    def process_result_value(self, value: str | None, dialect: Dialect) -> datetime | None:
        return None if value is None else datetime.fromisoformat(value)


def _values(enum: type[StrEnum]) -> list[str]:
    return [member.value for member in enum]


def _enum_column(enum: type[StrEnum]) -> SAEnum:
    # Store the value ("day"), not the member name, so plain sqlite3 reads match.
    return SAEnum(enum, values_callable=_values, native_enum=False, length=16)


class Fact(SQLModel, table=True):
    __tablename__ = FACT_TABLE

    id: int | None = Field(default=None, primary_key=True)
    detail: str
    relevance: int  # 1–10
    recorded_at: datetime = Field(sa_type=UtcDateTime, index=True)
    occurred_start: date | None = Field(default=None, index=True)
    occurred_end: date | None = Field(default=None, index=True)
    occurred_precision: Precision = Field(sa_type=_enum_column(Precision))  # ty: ignore[invalid-argument-type]
    superseded_by: int | None = Field(default=None, index=True)  # the newer fact that replaces this one
    revision: int = Field(index=True)  # bumped on every write; summaries refresh past a high-water mark
    source_conversation: str | None = None
    source_offset: int | None = None


class Tag(SQLModel, table=True):
    __tablename__ = TAG_TABLE

    name: str = Field(primary_key=True)  # canonical: lowercase, underscores; categories singular
    kind: TagKind = Field(sa_type=_enum_column(TagKind))  # ty: ignore[invalid-argument-type]
    description: str  # for an entity, its short profile
    created_at: datetime = Field(sa_type=UtcDateTime)


class TagAlias(SQLModel, table=True):
    __tablename__ = TAG_ALIAS_TABLE

    alias: str = Field(primary_key=True)
    tag: str = Field(foreign_key="tag.name", index=True)


class FactTag(SQLModel, table=True):
    __tablename__ = FACT_TAG_TABLE

    fact_id: int = Field(foreign_key="fact.id", primary_key=True)
    tag: str = Field(foreign_key="tag.name", primary_key=True, index=True)


class Period(SQLModel, table=True):
    __tablename__ = PERIOD_TABLE

    name: str = Field(primary_key=True)
    kind: PeriodKind = Field(sa_type=_enum_column(PeriodKind))  # ty: ignore[invalid-argument-type]
    start: date
    end: date  # inclusive
    summary: str = ""
    refreshed_at: datetime | None = Field(default=None, sa_type=UtcDateTime)


class TagSummary(SQLModel, table=True):
    __tablename__ = TAG_SUMMARY_TABLE

    tag: str = Field(foreign_key="tag.name", primary_key=True)
    summary: str
    refreshed_at: datetime = Field(sa_type=UtcDateTime)


class RefreshState(SQLModel, table=True):
    """The single row recording how far summaries have caught up."""

    __tablename__ = REFRESH_STATE_TABLE

    id: int = Field(default=1, primary_key=True)
    through_revision: int = 0
    refreshed_at: datetime | None = Field(default=None, sa_type=UtcDateTime)
    calendar_week_start: date | None = None  # Monday of the week the bucket calendar was last rolled to


class Gap(SQLModel, table=True):
    """Something memory knows exists but knows little about: a lead for the assistant's curiosity. The summariser rewrites the whole list."""

    __tablename__ = GAP_TABLE

    id: int | None = Field(default=None, primary_key=True)
    tag: str = Field(index=True)  # no foreign key: a tag merge must not fail on a gap
    text: str
    written_at: datetime = Field(sa_type=UtcDateTime)
    last_shown_at: datetime | None = Field(default=None, sa_type=UtcDateTime)
