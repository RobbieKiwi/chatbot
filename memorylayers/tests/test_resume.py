import shutil
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import memorylayers.entry.resume_command
from memorylayers.adapters.state_files import list_conversations, load_registry, save_conversation, update_registry, write_model
from memorylayers.domain.resume import choose_conversation, recent_turns
from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import ConversationState, PendingRegistration, SessionLink
from memorylayers.models.paths import ParentPaths
from memorylayers.models.transcript import Turn
from memorylayers.models.vocab import Role

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"
Run = Callable[[list[str]], tuple[int, str, str]]


def _turn(line: int) -> Turn:
    return Turn(role=Role.USER, text=f"t{line}", at=datetime(2026, 10, 3, tzinfo=UTC), session_id="s", line=line)


def test_choose_joins_only_a_recent_conversation() -> None:
    now = datetime(2026, 10, 3, 20, tzinfo=UTC)
    recent = ConversationState(id="a", started_at=now, last_activity=now - timedelta(hours=11))
    stale = ConversationState(id="b", started_at=now, last_activity=now - timedelta(hours=13))
    assert choose_conversation(conversations=[stale, recent], now=now, idle_hours=12) == recent
    assert choose_conversation(conversations=[recent, stale], now=now, idle_hours=12) is None


def test_recent_turns_print_each_turn_once() -> None:
    processed = [_turn(1), _turn(2), _turn(3)]
    assert [t.line for t in recent_turns(processed=processed, unprocessed=[_turn(4)], threshold_chars=100, recent_count=3)] == [2, 3, 4]
    many = [_turn(line) for line in range(4, 12)]
    assert [t.line for t in recent_turns(processed=processed, unprocessed=many, threshold_chars=100, recent_count=3)] == list(range(4, 12))


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(memorylayers.entry.resume_command, "spawn_runner", lambda *, paths, command: calls.append(command))
    return calls


def test_resume_joins_the_conversation_and_catches_up(paths: ParentPaths, tmp_path: Path, run_cli: Run, spawned: list[list[str]], local_persona: Path) -> None:
    write_model(path=paths.config, value=MemoryConfig(claude_executable=sys.executable))
    old = tmp_path / "s1.jsonl"
    shutil.copy(FIXTURE, old)
    now = datetime.now(UTC)
    save_conversation(
        paths=paths,
        state=ConversationState(
            id="c1", started_at=now, last_activity=now - timedelta(hours=1), rolling_summary="We talked tango.", sessions=[SessionLink(session_id="s1", transcript_path=old, processed_line=7)]
        ),
    )
    update_registry(paths=paths, change=lambda registry: setattr(registry, "pending", PendingRegistration(session_id="s2", transcript_path=tmp_path / "s2.jsonl", seen_at=now)))
    code, out, _ = run_cli(["resume"])
    assert code == 0
    assert "## This conversation so far\n\nWe talked tango." in out
    assert "Nova: Hello, Alex." in out and "Alex: Yesterday I went dancing with Jordan." in out
    registry = load_registry(paths=paths)
    assert registry.pending is None and registry.sessions == {"s2": "c1"}
    assert [link.session_id for link in list_conversations(paths=paths)[0].sessions] == ["s1", "s2"]
    assert spawned and "--catch-up" in spawned[0]


def test_resume_after_a_long_gap_starts_a_new_conversation(paths: ParentPaths, tmp_path: Path, run_cli: Run, spawned: list[list[str]]) -> None:
    write_model(path=paths.config, value=MemoryConfig(claude_executable=sys.executable))
    now = datetime.now(UTC)
    save_conversation(paths=paths, state=ConversationState(id="c1", started_at=now, last_activity=now - timedelta(days=2), rolling_summary="Old chat."))
    update_registry(paths=paths, change=lambda registry: setattr(registry, "pending", PendingRegistration(session_id="s9", transcript_path=tmp_path / "s9.jsonl", seen_at=now)))
    _, out, _ = run_cli(["resume"])
    assert "## Last conversation\n\nOld chat." in out
    assert len(list_conversations(paths=paths)) == 2


def test_resume_without_any_session_exits_2(paths: ParentPaths, run_cli: Run, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(memorylayers.entry.resume_command, "HOME", tmp_path)
    code, _, err = run_cli(["resume"])
    assert code == 2 and "/pk" in err


def test_resume_with_a_broken_persona_names_the_file(paths: ParentPaths, tmp_path: Path, run_cli: Run, spawned: list[list[str]], broken_persona: Path) -> None:
    write_model(path=paths.config, value=MemoryConfig(claude_executable=sys.executable))
    now = datetime.now(UTC)
    update_registry(paths=paths, change=lambda registry: setattr(registry, "pending", PendingRegistration(session_id="s9", transcript_path=tmp_path / "s9.jsonl", seen_at=now)))
    code, _, err = run_cli(["resume"])
    assert code == 2
    assert str(broken_persona) in err and "Traceback" not in err and len(err.strip().splitlines()) == 1
