import json
from pathlib import Path

from feedback.adapters.paths import feedback_path, logs_dir
from feedback.adapters.store import load_feedback
from feedback.entry.hook import HookPayload, handle_prompt, main
from feedback.tests.conftest import NOW, write_transcript


def _payload(*, tmp_path: Path, prompt: str) -> HookPayload:
    turns = [("user", f"message {index}") if index % 2 else ("assistant", f"reply {index}") for index in range(14)]
    return HookPayload(session_id="s1", transcript_path=write_transcript(path=tmp_path / "s1.jsonl", turns=turns), prompt=prompt)


def test_ordinary_messages_pass_untouched(tmp_path: Path, data_root: Path) -> None:
    assert handle_prompt(payload=_payload(tmp_path=tmp_path, prompt="hello"), path=feedback_path(parent="pk"), now=NOW) == ""
    assert not feedback_path(parent="pk").exists()


def test_feedback_is_logged_with_the_last_ten_turns_and_blocked(tmp_path: Path, data_root: Path) -> None:
    output = handle_prompt(payload=_payload(tmp_path=tmp_path, prompt="fb: fewer questions"), path=feedback_path(parent="pk"), now=NOW)
    assert json.loads(output) == {"decision": "block", "reason": "feedback #1 logged"}
    item = load_feedback(path=feedback_path(parent="pk")).items[0]
    assert item.text == "fewer questions"
    assert item.context.startswith("Nova: reply 4\n\nthe user: message 5")
    assert item.context.endswith("the user: message 13")


def test_the_context_takes_its_names_from_a_local_persona(tmp_path: Path, data_root: Path, shipped_persona: Path) -> None:
    local = shipped_persona / "local"
    local.mkdir()
    (local / "persona.json").write_text(json.dumps({"assistant_name": "Iris", "user_name": "Sam"}), encoding="utf-8")
    handle_prompt(payload=_payload(tmp_path=tmp_path, prompt="fb: fewer questions"), path=feedback_path(parent="pk"), now=NOW)
    assert load_feedback(path=feedback_path(parent="pk")).items[0].context.endswith("Iris: reply 12\n\nSam: message 13")


def test_a_broken_persona_blocks_the_feedback_and_names_the_file(tmp_path: Path, data_root: Path, shipped_persona: Path) -> None:
    local = shipped_persona / "local"
    local.mkdir()
    (local / "persona.json").write_text("{ nope", encoding="utf-8")
    output = json.loads(handle_prompt(payload=_payload(tmp_path=tmp_path, prompt="fb: fewer questions"), path=feedback_path(parent="pk"), now=NOW))
    assert output["decision"] == "block" and str(local / "persona.json") in output["reason"]
    assert not feedback_path(parent="pk").exists()


def test_feedback_files_into_a_fresh_data_root(tmp_path: Path, data_root: Path) -> None:
    assert not data_root.exists()
    handle_prompt(payload=_payload(tmp_path=tmp_path, prompt="fb: fewer questions"), path=feedback_path(parent="pk"), now=NOW)
    assert feedback_path(parent="pk").exists()


def test_a_note_reopens_its_item(tmp_path: Path, data_root: Path) -> None:
    path = feedback_path(parent="pk")
    handle_prompt(payload=_payload(tmp_path=tmp_path, prompt="fb: fewer questions"), path=path, now=NOW)
    output = handle_prompt(payload=_payload(tmp_path=tmp_path, prompt="fb: #1 still too many"), path=path, now=NOW)
    assert json.loads(output)["reason"] == "feedback #1 logged"
    assert [note.text for note in load_feedback(path=path).items[0].notes] == ["still too many"]


def test_empty_feedback_is_blocked_and_files_nothing(tmp_path: Path, data_root: Path) -> None:
    output = handle_prompt(payload=_payload(tmp_path=tmp_path, prompt="fb:"), path=feedback_path(parent="pk"), now=NOW)
    assert json.loads(output) == {"decision": "block", "reason": "say what you'd like changed"}
    assert not feedback_path(parent="pk").exists()


def test_an_invalid_feedback_file_is_logged_and_the_message_passes(tmp_path: Path, data_root: Path) -> None:
    path = feedback_path(parent="pk")
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")
    stdin = json.dumps({"session_id": "s1", "transcript_path": str(tmp_path / "none.jsonl"), "prompt": "fb: hello", "hook_event_name": "UserPromptSubmit"}).encode()
    assert main(argv=["--parent", "pk"], stdin_bytes=stdin) == ""
    assert "Traceback" in (logs_dir() / "hook.log").read_text(encoding="utf-8")
