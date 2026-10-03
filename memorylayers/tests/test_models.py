from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import ConversationState, PendingNote, SessionLink
from memorylayers.models.memory import Fact, FactTag, Period, RefreshState, Tag, TagAlias, TagSummary
from memorylayers.models.vocab import Precision


def test_config_defaults_match_the_spec() -> None:
    config = MemoryConfig()
    assert config.scribe_threshold_chars == 8000
    assert config.overlap_fraction == 0.3
    assert config.idle_hours == 12
    assert config.pending_settle_runs == 2
    assert config.refresh_after_facts == 10
    assert config.duplicate_overlap == 0.5
    assert config.stale_lock_minutes == 30
    assert config.max_consecutive_failures == 3
    assert config.local_timezone == "UTC"


def test_config_rejects_unknown_settings() -> None:
    with pytest.raises(ValidationError):
        MemoryConfig.model_validate({"scribe_threshold": 10})


def test_conversation_state_round_trips_through_json() -> None:
    now = datetime(2026, 10, 3, 20, 0, tzinfo=UTC)
    state = ConversationState(
        id="2026-10-03-220000",
        started_at=now,
        last_activity=now,
        sessions=[SessionLink(session_id="abc", transcript_path=Path("t.jsonl"), processed_line=4)],
        pending_notes=[PendingNote(number=1, text="may be moving to Bonn")],
        ledger=[3, 9],
    )
    assert ConversationState.model_validate_json(state.model_dump_json()) == state


def test_table_names_follow_the_spec() -> None:
    names = [model.__tablename__ for model in (Fact, Tag, TagAlias, FactTag, Period, TagSummary, RefreshState)]
    assert names == ["fact", "tag", "tag_alias", "fact_tag", "period", "tag_summary", "refresh_state"]


def test_precision_values() -> None:
    assert [p.value for p in Precision] == ["day", "month", "year", "decade", "unknown", "timeless"]
