import shutil
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from memorylayers.adapters.transcripts import newest_session, project_transcript_dir, read_complete_lines, read_conversation_turns
from memorylayers.models.conversation import ConversationState, SessionLink

FIXTURE = Path(__file__).parent / "fixtures" / "transcript.jsonl"
BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 10, 3, tzinfo=UTC)


def test_a_line_still_being_written_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_bytes(b'{"a": 1}\n{"b": 2}\n{"c": ')
    assert read_complete_lines(path=path) == ['{"a": 1}', '{"b": 2}']
    assert read_complete_lines(path=tmp_path / "missing.jsonl") == []


def test_turns_split_at_the_processed_line(tmp_path: Path) -> None:
    transcript = tmp_path / "s1.jsonl"
    shutil.copy(FIXTURE, transcript)
    state = ConversationState(id="c", started_at=NOW, last_activity=NOW, sessions=[SessionLink(session_id="s1", transcript_path=transcript, processed_line=7)])
    turns = read_conversation_turns(state=state, tz=BERLIN)
    assert [turn.line for turn in turns.processed] == [6]
    assert [turn.line for turn in turns.unprocessed] == [8, 12]
    assert turns.ends == {"s1": 13}
    assert read_conversation_turns(state=state, tz=BERLIN, include_processed=False).processed == []


def test_newest_session_in_the_project_folder(tmp_path: Path) -> None:
    folder = tmp_path / ".claude" / "projects" / "c--Users-alex-chatbot"
    folder.mkdir(parents=True)
    (folder / "old.jsonl").write_text("{}\n")
    newest = folder / "new.jsonl"
    newest.write_text("{}\n")
    project = Path("C:/Users/alex/chatbot")
    assert project_transcript_dir(project_dir=project, home=tmp_path) == folder
    assert newest_session(project_dir=project, home=tmp_path) == ("new", newest)
