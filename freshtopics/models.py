from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TopicEntry(BaseModel):
    inserted: datetime
    parent_name: str
    phrase: str
    initiator: str
    score: int = Field(ge=1, le=10)

    @field_validator("initiator")
    def validate_initator(cls, v: str) -> str:
        if v not in ("skill", "user"):
            raise ValueError("Must be skill or user")
        return v

    @field_validator("phrase")
    def validate_phrase(cls, phrase: str) -> str:
        if not phrase or not isinstance(phrase, str):
            raise ValueError("Topic phrase must be a non-empty string")

        # Normalize
        phrase = phrase.strip().lower()

        # Check word count
        words = phrase.split()
        if len(words) < 3 or len(words) > 8:
            raise ValueError(f"Topic phrase must be 3-8 words, got {len(words)}: '{phrase}'")

        return phrase


class TopicsData(BaseModel):
    terrible_topics: list[str] = Field(default=[])
    excellent_topics: list[str] = Field(default=[])
    topics: list[TopicEntry] = Field(default=[])


class Seeds(BaseModel):
    """Random starting points for the muse: two concrete nouns and a field of knowledge."""

    words: tuple[str, str]
    subject: str


class Probe(BaseModel):
    """A gap in memory, proposed as a topic in place of seeds."""

    tag: str
    text: str
