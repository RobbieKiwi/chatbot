from collections.abc import Callable
from datetime import UTC, datetime

from memorylayers.adapters.state_files import load_conversation, save_conversation
from memorylayers.adapters.store import MemoryStore
from memorylayers.models.conversation import ConversationState
from memorylayers.models.paths import ParentPaths
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import TagKind
from memorylayers.tests.conftest import NOW

Run = Callable[[list[str]], tuple[int, str, str]]


def _seed(paths: ParentPaths) -> None:
    with MemoryStore(db_path=paths.db) as store:
        store.create_tag(new=NewTag(name="friend", kind=TagKind.CATEGORY, description="friends"), now=NOW)
        store.create_tag(new=NewTag(name="jordan", kind=TagKind.ENTITY, description="tango friend"), now=NOW)
    at = datetime(2026, 10, 3, 18, 0, tzinfo=UTC)
    save_conversation(paths=paths, state=ConversationState(id="c1", started_at=at, last_activity=at))


def test_store_writes_a_fact_and_records_it_in_the_ledger(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    code, out, _ = run_cli(["store", "--detail", "Jordan teaches tango on Tuesdays", "--relevance", "6", "--tags", "jordan,friends", "--timeless", "--conversation", "c1"])
    assert (code, out.strip()) == (0, "stored fact #1")
    assert load_conversation(paths=paths, conversation_id="c1").ledger == [1]


def test_store_rejects_relevance_zero_and_bad_dates(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    assert run_cli(["store", "--detail", "x", "--relevance", "0", "--tags", "jordan", "--timeless"])[0] == 2
    code, _, err = run_cli(["store", "--detail", "x", "--relevance", "5", "--tags", "jordan", "--occurred", "yesterday"])
    assert code == 2 and "YYYY-MM-DD" in err


def test_store_refuses_an_unknown_category_until_registered(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    code, _, err = run_cli(["store", "--detail", "Alex dances bachata", "--relevance", "5", "--tags", "dance", "--timeless"])
    assert code == 2 and "--new-category" in err
    code, out, _ = run_cli(["store", "--detail", "Alex dances bachata", "--relevance", "5", "--tags", "dance", "--new-category", "dance: dancing of any kind", "--timeless"])
    assert code == 0


def test_store_returns_duplicates_instead_of_writing(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    run_cli(["store", "--detail", "Jordan teaches tango on Tuesdays", "--relevance", "6", "--tags", "jordan", "--timeless"])
    code, _, err = run_cli(["store", "--detail", "Jordan teaches tango every Tuesday", "--relevance", "6", "--tags", "jordan", "--timeless"])
    assert code == 2
    assert "#1" in err and "--force-new" in err
    code, out, _ = run_cli(["store", "--detail", "Jordan teaches tango every Tuesday", "--relevance", "6", "--tags", "jordan", "--timeless", "--force-new"])
    assert out.strip() == "stored fact #2"


def test_update_and_supersede(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    run_cli(["store", "--detail", "Jordan lives in Pankow", "--relevance", "5", "--tags", "jordan", "--timeless"])
    run_cli(["store", "--detail", "Jordan moved to Bonn", "--relevance", "5", "--tags", "jordan", "--occurred", "2026-09", "--force-new"])
    assert run_cli(["update", "1", "--relevance", "4", "--occurred", "2024"])[0] == 0
    assert run_cli(["supersede", "1", "--by", "2"])[0] == 0
    _, out, _ = run_cli(["facts", "jordan"])
    assert "#1" not in out and "#2" in out


def test_pending_notes_and_rolling_summary(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    run_cli(["pending", "add", "--conversation", "c1", "--text", "may be moving to Bonn"])
    run_cli(["pending", "add", "--conversation", "c1", "--text", "thinking about a new job"])
    run_cli(["pending", "refine", "--conversation", "c1", "--number", "1", "--text", "moving to Bonn in spring"])
    run_cli(["pending", "drop", "--conversation", "c1", "--number", "2"])
    run_cli(["rolling-summary", "set", "--conversation", "c1", "--text", "We talked about tango."])
    state = load_conversation(paths=paths, conversation_id="c1")
    assert [(note.number, note.text) for note in state.pending_notes] == [(1, "moving to Bonn in spring")]
    assert state.rolling_summary == "We talked about tango."
    assert run_cli(["pending", "drop", "--conversation", "c1", "--number", "9"])[0] == 2


def test_rolling_summary_has_a_word_limit(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    assert run_cli(["rolling-summary", "set", "--conversation", "c1", "--text", "word " * 500])[0] == 2
