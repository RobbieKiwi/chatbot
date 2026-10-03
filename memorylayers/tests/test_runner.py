import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import memorylayers.adapters.prompts
import memorylayers.entry.runner
from memorylayers.adapters.locks import read_lock, try_create_lock
from memorylayers.adapters.state_files import load_conversation, load_summariser_health, save_conversation, write_model
from memorylayers.adapters.store import MemoryStore
from memorylayers.entry.cli import main
from memorylayers.entry.runner import acquire, run_scribe, run_summariser
from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import ConversationState, SessionLink
from memorylayers.models.paths import ParentPaths
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import TagKind, WorkerKind
from memorylayers.models.worker import RunRecord
from memorylayers.tools.occurred import TIMELESS

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"
NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)


@pytest.fixture
def setup(paths: ParentPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_persona: Path) -> ParentPaths:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "scribe.md").write_text("Run $run\n$new_turns", encoding="utf-8")
    (prompts / "summariser.md").write_text("Run $run\n$plan\n$tag_sections", encoding="utf-8")
    monkeypatch.setattr(memorylayers.adapters.prompts, "PROMPTS_DIR", prompts)
    write_model(path=paths.config, value=MemoryConfig(scribe_threshold_chars=10))
    transcript = tmp_path / "s1.jsonl"
    shutil.copy(FIXTURE, transcript)
    save_conversation(paths=paths, state=ConversationState(id="c1", started_at=NOW, last_activity=NOW, sessions=[SessionLink(session_id="s1", transcript_path=transcript)]))
    with MemoryStore(db_path=paths.db) as store:
        store.create_tag(new=NewTag(name="jordan", kind=TagKind.ENTITY, description="tango friend"), now=NOW)
    return paths


def _now() -> datetime:
    return NOW


def _cli(*argv: str) -> None:
    assert main(argv=[*argv, "--parent", "pk"]) == 0


def test_a_scribe_run_files_and_commits(setup: ParentPaths) -> None:
    calls = []

    def fake_claude(*, model: str, allowed_tools: list[str], brief_path: Path, log_path: Path, timeout_s: float) -> int:
        calls.append(brief_path.read_text(encoding="utf-8"))
        record = read_lock(paths=setup, kind=WorkerKind.SCRIBE)
        assert record is not None
        run_id = record.run_id
        _cli("store", "--detail", "Alex went dancing with Jordan", "--relevance", "6", "--tags", "jordan", "--occurred", "2026-10-01", "--conversation", "c1")
        _cli("commit", "--run", run_id)
        return 0

    # Catch-up files the whole tail in one window, whatever its length.
    run_scribe(paths=setup, config=MemoryConfig(), conversation_id="c1", catch_up=True, call_claude=fake_claude, now=_now)
    state = load_conversation(paths=setup, conversation_id="c1")
    assert len(calls) == 1
    assert "Alex: Yesterday I went dancing with Jordan." in calls[0]
    assert state.ledger == [1]
    assert state.sessions[0].processed_line == 13
    assert read_lock(paths=setup, kind=WorkerKind.SCRIBE) is None


def test_runs_that_never_commit_stop_the_scribe(setup: ParentPaths) -> None:
    calls = []

    def silent_claude(**_: object) -> int:
        calls.append(1)
        return 1

    config = MemoryConfig(scribe_threshold_chars=10, max_consecutive_failures=3)
    for _ in range(4):
        run_scribe(paths=setup, config=config, conversation_id="c1", catch_up=False, call_claude=silent_claude, now=_now)
    state = load_conversation(paths=setup, conversation_id="c1")
    assert len(calls) == 3
    assert state.scribe_health.stopped_reason is not None
    assert state.sessions[0].processed_line == 0


def test_acquire_counts_an_abandoned_run_as_a_failure(setup: ParentPaths) -> None:
    try_create_lock(paths=setup, record=RunRecord(run_id="old", kind=WorkerKind.SCRIBE, pid=-1, started_at=NOW, deadline=NOW + timedelta(minutes=30), conversation_id="c1"))
    record = acquire(paths=setup, config=MemoryConfig(), kind=WorkerKind.SCRIBE, now=NOW, timeout_minutes=30, conversation_id="c1")
    assert record is not None and record.run_id != "old"
    assert load_conversation(paths=setup, conversation_id="c1").scribe_health.consecutive_failures == 1


def test_a_summariser_run_commits_its_high_water_mark(setup: ParentPaths) -> None:
    with MemoryStore(db_path=setup.db) as store:
        for number in range(3):
            store.add_fact(detail=f"Jordan fact {number}", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
    briefs = []

    def fake_claude(*, model: str, allowed_tools: list[str], brief_path: Path, log_path: Path, timeout_s: float) -> int:
        briefs.append(brief_path.read_text(encoding="utf-8"))
        record = read_lock(paths=setup, kind=WorkerKind.SUMMARISER)
        assert record is not None
        run_id = record.run_id
        _cli("tag-summary", "set", "--tag", "jordan", "--text", "Jordan, a tango friend.")
        _cli("refresh", "commit", "--run", run_id)
        return 0

    run_summariser(paths=setup, config=MemoryConfig(), call_claude=fake_claude, now=_now, timeout_minutes=30)
    assert "### tag jordan" in briefs[0]
    with MemoryStore(db_path=setup.db) as store:
        assert store.refresh_state().through_revision == 3
    assert load_summariser_health(paths=setup).consecutive_failures == 0
    assert read_lock(paths=setup, kind=WorkerKind.SUMMARISER) is None


def test_commit_refuses_an_unknown_run(setup: ParentPaths) -> None:
    assert main(argv=["commit", "--run", "nope", "--parent", "pk"]) == 2


def test_a_worker_with_a_broken_persona_stops_naming_the_file(paths: ParentPaths, broken_persona: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(memorylayers.entry.runner, "find_claude", lambda *, executable: "claude")
    monkeypatch.setattr(memorylayers.entry.runner, "run_claude", lambda **kwargs: pytest.fail("a worker ran without a persona"))
    assert memorylayers.entry.runner.main(argv=["--parent", "pk", "--kind", "summariser"]) == 1
    err = capsys.readouterr().err
    assert str(broken_persona) in err and len(err.strip().splitlines()) == 1
    assert read_lock(paths=paths, kind=WorkerKind.SUMMARISER) is None
