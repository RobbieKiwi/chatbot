import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import mood.entry.stop_hook
from mood.adapters.locks import observer_lock_path, try_lock
from mood.adapters.paths import mood_paths
from mood.adapters.sessions import save_mood
from mood.entry.stop_hook import StopPayload, handle_stop, main
from mood.tests.conftest import NOW, mood_state

PAYLOAD = StopPayload(session_id="s1", transcript_path=Path("s1.jsonl"))


def _stop(*, now: datetime = NOW) -> list[list[str]]:
    spawned: list[list[str]] = []
    handle_stop(payload=PAYLOAD, paths=mood_paths(parent="pk"), now=now, spawn=spawned.append)
    return spawned


def test_no_mood_no_observer(data_root: Path) -> None:
    assert _stop() == []


def test_the_observer_is_launched_holding_the_lock(data_root: Path) -> None:
    save_mood(paths=mood_paths(parent="pk"), session_id="s1", state=mood_state())
    assert _stop() == [[sys.executable, "-m", "mood", "observe", "--parent", "pk", "--session", "s1", "--transcript", "s1.jsonl"]]
    assert observer_lock_path(paths=mood_paths(parent="pk"), session_id="s1").exists()


def test_a_running_observer_is_not_joined(data_root: Path) -> None:
    paths = mood_paths(parent="pk")
    save_mood(paths=paths, session_id="s1", state=mood_state())
    assert try_lock(path=observer_lock_path(paths=paths, session_id="s1"), now=NOW, stale_after=timedelta(minutes=5))
    assert _stop(now=NOW + timedelta(seconds=30)) == []
    assert len(_stop(now=NOW + timedelta(hours=1))) == 1  # an observer that died long ago


def test_a_failed_launch_releases_the_lock(data_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = mood_paths(parent="pk")
    save_mood(paths=paths, session_id="s1", state=mood_state())

    def spawn(command: list[str]) -> None:
        raise OSError("no python")

    monkeypatch.setattr(mood.entry.stop_hook, "spawn_observer", spawn)
    stdin = json.dumps({"session_id": "s1", "transcript_path": "s1.jsonl", "hook_event_name": "Stop", "stop_hook_active": False}).encode()
    main(argv=["--parent", "pk"], stdin_bytes=stdin)
    assert not observer_lock_path(paths=paths, session_id="s1").exists()
    assert "no python" in (paths.logs / "stop_hook.log").read_text(encoding="utf-8")
