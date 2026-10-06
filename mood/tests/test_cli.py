import os
from pathlib import Path

from mood.adapters.paths import mood_paths
from mood.adapters.sessions import save_mood
from mood.entry.cli import show
from mood.tests.conftest import mood_state


def test_show_reports_the_most_recently_updated_session(data_root: Path) -> None:
    paths = mood_paths(parent="pk")
    save_mood(paths=paths, session_id="older", state=mood_state(melancholy=8))
    save_mood(paths=paths, session_id="newer", state=mood_state(irritation=8))
    os.utime(paths.sessions / "older.json", (0, 0))
    report = show(paths=paths, session_id=None, history_count=5)
    assert report.startswith("session newer\n") and "irritation 8" in report


def test_show_says_when_there_is_no_mood(data_root: Path) -> None:
    assert show(paths=mood_paths(parent="pk"), session_id=None, history_count=5).startswith("no mood for any session")
