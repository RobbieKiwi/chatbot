import pytest
from pydantic import ValidationError

from memorylayers.models.config import MemoryConfig
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


def test_table_names_follow_the_spec() -> None:
    names = [model.__tablename__ for model in (Fact, Tag, TagAlias, FactTag, Period, TagSummary, RefreshState)]
    assert names == ["fact", "tag", "tag_alias", "fact_tag", "period", "tag_summary", "refresh_state"]


def test_precision_values() -> None:
    assert [p.value for p in Precision] == ["day", "month", "year", "decade", "unknown", "timeless"]
