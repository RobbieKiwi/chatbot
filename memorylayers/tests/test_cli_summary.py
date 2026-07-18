from collections.abc import Callable

from memorylayers.adapters.store import MemoryStore
from memorylayers.models.paths import ParentPaths
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import TagKind
from memorylayers.tests.conftest import NOW
from memorylayers.tools.occurred import parse_occurred

Run = Callable[[list[str]], tuple[int, str, str]]


def _seed(paths: ParentPaths) -> None:
    with MemoryStore(db_path=paths.db) as store:
        store.create_tag(new=NewTag(name="friend", kind=TagKind.CATEGORY, description="friends"), now=NOW)
        store.create_tag(new=NewTag(name="friends", kind=TagKind.CATEGORY, description="duplicate"), now=NOW)
        store.create_tag(new=NewTag(name="jordan", kind=TagKind.ENTITY, description="tango friend"), now=NOW)
        for number in range(3):
            store.add_fact(detail=f"Jordan fact {number}", relevance=5, occurred=parse_occurred(text="2026-07"), tags=["jordan", "friends"], source_conversation=None, now=NOW)


def test_refresh_plan_lists_what_is_due(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    _, out, _ = run_cli(["refresh-plan"])
    assert "Tags: friends, jordan" in out
    assert "2026-07" in out or "2026 Q3" in out


def test_summaries_are_written(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    assert run_cli(["tag-summary", "set", "--tag", "jordan", "--text", "Jordan is a tango friend."])[0] == 0
    assert run_cli(["period", "set", "--name", "2026 Q3", "--text", "Tango summer."])[0] == 0
    assert run_cli(["era", "set", "--name", "Germany", "--start", "2020-01", "--text", "Life in Germany."])[0] == 0
    assert run_cli(["high-level-summary", "set", "--text", "Alex, a Canadian in Berlin."])[0] == 0
    assert paths.summary.read_text(encoding="utf-8").startswith("Refreshed: ")
    _, out, _ = run_cli(["periods"])
    assert "Germany (era) 2020-01-01..ongoing" in out


def test_period_set_rejects_unknown_names(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    code, _, err = run_cli(["period", "set", "--name", "summer", "--text", "x"])
    assert code == 2 and "2026 Q3" in err


def test_tag_summary_has_a_word_limit(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    assert run_cli(["tag-summary", "set", "--tag", "jordan", "--text", "word " * 1300])[0] == 2


def test_consolidator_commands(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    assert run_cli(["tag", "merge", "--from", "friends", "--into", "friend"])[0] == 0
    assert run_cli(["tag", "rename", "--from", "jordan", "--to", "jordan_ramos"])[0] == 0
    assert run_cli(["tag", "describe", "--name", "friend", "--description", "people Alex is close to"])[0] == 0
    assert run_cli(["alias", "add", "--alias", "jordy", "--tag", "jordan_ramos"])[0] == 0
    assert run_cli(["fact", "retag", "1", "--tags", "jordy"])[0] == 0
    _, out, _ = run_cli(["tags"])
    assert "Entities: jordan_ramos (3)" in out
    assert "friend (2)" in out
