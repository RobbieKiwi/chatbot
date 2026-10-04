import json
import random
from pathlib import Path

import pytest

from mood.adapters.paths import mood_paths
from mood.adapters.sessions import load_mood, save_mood
from mood.entry.common import HookPayload
from mood.entry.prompt_hook import handle_prompt, main
from mood.tests.conftest import NOW, mood_state


def _payload(*, prompt: str, session: str = "s1") -> HookPayload:
    return HookPayload(session_id=session, transcript_path=Path("t.jsonl"), prompt=prompt)


@pytest.mark.parametrize("prompt", ["/pk", "/pk let's talk", "<command-message>pk</command-message>\n<command-name>/pk</command-name>"])
def test_registration_rolls_a_fresh_mood_and_shows_it(data_root: Path, prompt: str) -> None:
    paths = mood_paths(parent="pk")
    output = handle_prompt(payload=_payload(prompt=prompt), paths=paths, now=NOW, rng=random.Random(4))
    state = load_mood(paths=paths, session_id="s1")
    assert state is not None and state.rolled_at == NOW
    assert output.startswith('<mood presence="') and output.endswith("</mood>")


def test_later_messages_carry_the_mood(data_root: Path) -> None:
    paths = mood_paths(parent="pk")
    save_mood(paths=paths, session_id="s1", state=mood_state(melancholy=7, presence=3))
    assert handle_prompt(payload=_payload(prompt="hello"), paths=paths, now=NOW, rng=random.Random(0)).startswith('<mood presence="3/10">melancholy 7 · ')


def test_sessions_without_a_mood_get_nothing(data_root: Path) -> None:
    assert handle_prompt(payload=_payload(prompt="hello", session="other"), paths=mood_paths(parent="pk"), now=NOW, rng=random.Random(0)) == ""


def test_a_second_registration_rerolls(data_root: Path) -> None:
    paths = mood_paths(parent="pk")
    save_mood(paths=paths, session_id="s1", state=mood_state(melancholy=7))
    handle_prompt(payload=_payload(prompt="/pk"), paths=paths, now=NOW, rng=random.Random(4))
    state = load_mood(paths=paths, session_id="s1")
    assert state is not None and state != mood_state(melancholy=7)


def test_unsafe_session_ids_are_refused(data_root: Path) -> None:
    with pytest.raises(ValueError):
        load_mood(paths=mood_paths(parent="pk"), session_id="../escape")


def test_main_logs_failures_and_stays_silent(data_root: Path) -> None:
    assert main(argv=["--parent", "pk"], stdin_bytes=b"{not json") == ""
    assert "Traceback" in (mood_paths(parent="pk").logs / "prompt_hook.log").read_text(encoding="utf-8")


def test_main_reads_stdin(data_root: Path) -> None:
    stdin = json.dumps({"session_id": "s1", "transcript_path": "x.jsonl", "prompt": "/pk", "hook_event_name": "UserPromptSubmit"}).encode()
    assert main(argv=["--parent", "pk"], stdin_bytes=stdin).startswith("<mood ")
