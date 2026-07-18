from collections.abc import Callable

from memorylayers.adapters.store import MemoryStore
from memorylayers.models.paths import ParentPaths
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import TagKind
from memorylayers.tests.conftest import NOW

Run = Callable[[list[str]], tuple[int, str, str]]


def _seed(paths: ParentPaths) -> None:
    with MemoryStore(db_path=paths.db) as store:
        store.create_tag(new=NewTag(name="friend", kind=TagKind.CATEGORY, description="friends"), now=NOW)
        store.create_tag(new=NewTag(name="jordan", kind=TagKind.ENTITY, description="tango friend"), now=NOW)


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
