"""The one-off migration of the legacy flat memory into layered memory."""

from datetime import datetime

from pydantic import BaseModel, Field


class LegacyFact(BaseModel):
    id: int
    detail: str
    relevance: int
    inserted: datetime  # naive, in the configured local timezone
    tags: list[str]


class ProposedCategory(BaseModel):
    name: str
    description: str


class ProposedEntity(BaseModel):
    name: str
    profile: str
    aliases: list[str] = Field(default_factory=list)


class ProposedFact(BaseModel):
    id: int
    tags: list[str]
    occurred: str  # an --occurred value, "timeless" or "unknown"


class ProposedSupersession(BaseModel):
    old_id: int
    new_id: int


class ProposedEra(BaseModel):
    name: str
    start: str  # an --occurred value
    end: str | None = None  # None while the era is ongoing


class MigrationProposal(BaseModel):
    categories: list[ProposedCategory]
    entities: list[ProposedEntity]
    category_aliases: dict[str, str] = Field(default_factory=dict)  # alias -> category
    facts: list[ProposedFact]
    supersessions: list[ProposedSupersession] = Field(default_factory=list)
    eras: list[ProposedEra] = Field(default_factory=list)
