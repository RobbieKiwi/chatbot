import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from memorylayers.adapters.locks import try_create_lock
from memorylayers.adapters.paths import PROJECT_ROOT
from memorylayers.adapters.state_files import load_conversation, load_registry, save_conversation, update_registry, write_model
from memorylayers.adapters.store import MemoryStore
from memorylayers.entry.hook import HookPayload, handle_prompt, main
from memorylayers.models.config import MemoryConfig
from memorylayers.models.conversation import ConversationState, SessionLink
from memorylayers.models.paths import ParentPaths
from memorylayers.models.views import NewGap, NewTag
from memorylayers.models.vocab import TagKind, WorkerKind
from memorylayers.models.worker import RunRecord
from memorylayers.tools.occurred import TIMELESS

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"
NOW = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)


@pytest.fixture
def registered(paths: ParentPaths, tmp_path: Path) -> ParentPaths:
    transcript = tmp_path / "s1.jsonl"
    shutil.copy(FIXTURE, transcript)
    write_model(path=paths.config, value=MemoryConfig(scribe_threshold_chars=10, refresh_after_facts=1))
    save_conversation(paths=paths, state=ConversationState(id="c1", started_at=NOW, last_activity=NOW, sessions=[SessionLink(session_id="s1", transcript_path=transcript)]))
    update_registry(paths=paths, change=lambda registry: registry.sessions.update({"s1": "c1"}))
    with MemoryStore(db_path=paths.db) as store:
        store.create_tag(new=NewTag(name="jordan", kind=TagKind.ENTITY, description="tango friend"), now=NOW)
        store.add_fact(detail="Jordan dances", relevance=5, occurred=TIMELESS, tags=["jordan"], source_conversation=None, now=NOW)
        store.replace_gaps(gaps=[NewGap(tag="jordan", text="Jordan is a friend, but nothing is known about how they met.")], now=NOW)
    return paths


def _payload(*, session: str = "s1", prompt: str = "Jordan called me") -> HookPayload:
    return HookPayload(session_id=session, transcript_path=Path("t.jsonl"), prompt=prompt)


class _Dice(random.Random):
    def __init__(self, *, roll: float) -> None:
        super().__init__(0)
        self._roll = roll

    def random(self) -> float:
        return self._roll


def _run(paths: ParentPaths, payload: HookPayload, *, claude: bool = True, roll: float = 0.99) -> tuple[str, list[list[str]]]:
    spawned: list[list[str]] = []
    output = handle_prompt(payload=payload, paths=paths, now=NOW, spawn=spawned.append, claude_available=lambda: claude, rng=_Dice(roll=roll))
    return output, spawned


def test_the_slash_command_records_a_pending_registration(paths: ParentPaths) -> None:
    output, spawned = _run(paths, _payload(session="new", prompt="/pk"))
    assert (output, spawned) == ("", [])
    pending = load_registry(paths=paths).pending
    assert pending is not None
    assert pending.session_id == "new"


def test_unregistered_sessions_are_ignored(registered: ParentPaths) -> None:
    assert _run(registered, _payload(session="other")) == ("", [])


def test_hints_once_per_conversation(registered: ParentPaths) -> None:
    output, _ = _run(registered, _payload())
    assert output == "<memory-hints>jordan (entity, 1 facts)</memory-hints>"
    assert _run(registered, _payload())[0] == ""
    assert load_conversation(paths=registered, conversation_id="c1").hints_shown == ["jordan"]


def test_due_workers_are_launched(registered: ParentPaths) -> None:
    _, spawned = _run(registered, _payload())
    kinds = [command[command.index("--kind") + 1] for command in spawned]
    assert kinds == ["scribe", "summariser"]
    assert spawned[0][spawned[0].index("--conversation") + 1] == "c1"


def test_a_live_lock_launches_nothing(registered: ParentPaths) -> None:
    for kind in (WorkerKind.SCRIBE, WorkerKind.SUMMARISER):
        try_create_lock(paths=registered, record=RunRecord(run_id="r", kind=kind, pid=os.getpid(), started_at=NOW, deadline=NOW + timedelta(hours=1)))
    assert _run(registered, _payload())[1] == []


def test_without_claude_nothing_launches(registered: ParentPaths) -> None:
    assert _run(registered, _payload(), claude=False)[1] == []


def test_malformed_input_is_logged_and_silent(registered: ParentPaths) -> None:
    assert main(argv=["--parent", "pk"], stdin_bytes=b"{not json") == ""
    assert "Traceback" in (registered.logs / "hook.log").read_text(encoding="utf-8")


def test_main_reads_stdin_json(registered: ParentPaths) -> None:
    stdin = json.dumps({"session_id": "other", "transcript_path": "x.jsonl", "prompt": "hi", "hook_event_name": "UserPromptSubmit"}).encode()
    assert main(argv=["--parent", "pk"], stdin_bytes=stdin) == ""


def test_the_hook_never_imports_sqlmodel() -> None:
    probe = "import sys, memorylayers.entry.hook; print(any(name.split('.')[0] in ('sqlmodel', 'sqlalchemy') for name in sys.modules))"
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, cwd=PROJECT_ROOT, check=True)
    assert result.stdout.strip() == "False"


CURIOSITY = '<curiosity tag="jordan">Jordan is a friend, but nothing is known about how they met.</curiosity>'


def test_curiosity_waits_for_the_fourth_message_then_rests(registered: ParentPaths) -> None:
    outputs = [_run(registered, _payload(prompt="hello"), roll=0.0)[0] for _ in range(5)]
    assert outputs == ["", "", "", CURIOSITY, ""]  # the only gap is on its cooldown after the fourth
    assert load_conversation(paths=registered, conversation_id="c1").messages_seen == 5


def test_curiosity_follows_the_memory_hints(registered: ParentPaths) -> None:
    for _ in range(3):
        _run(registered, _payload(prompt="hello"))
    assert _run(registered, _payload(), roll=0.0)[0] == f"<memory-hints>jordan (entity, 1 facts)</memory-hints>\n{CURIOSITY}"


def test_no_curiosity_when_the_dice_say_no(registered: ParentPaths) -> None:
    assert [_run(registered, _payload(prompt="hello"))[0] for _ in range(6)] == [""] * 6


def test_hints_survive_a_database_without_gaps(registered: ParentPaths) -> None:
    with sqlite3.connect(registered.db) as connection:
        connection.execute("DROP TABLE gap")
    for _ in range(3):
        _run(registered, _payload(prompt="hello"), roll=0.0)
    assert _run(registered, _payload(), roll=0.0)[0] == "<memory-hints>jordan (entity, 1 facts)</memory-hints>"
