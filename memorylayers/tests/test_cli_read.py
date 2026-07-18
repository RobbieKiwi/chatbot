import os
import subprocess
import sys
from collections.abc import Callable

from memorylayers.adapters.paths import PROJECT_ROOT
from memorylayers.adapters.store import MemoryStore
from memorylayers.models.paths import ParentPaths
from memorylayers.models.views import NewTag
from memorylayers.models.vocab import TagKind
from memorylayers.tests.conftest import NOW
from memorylayers.tools.calendar import parse_bucket_name
from memorylayers.tools.occurred import parse_occurred

Run = Callable[[list[str]], tuple[int, str, str]]


def _seed(paths: ParentPaths, *, facts: int = 2) -> None:
    with MemoryStore(db_path=paths.db) as store:
        store.create_tag(new=NewTag(name="friend", kind=TagKind.CATEGORY, description="Alex's friends"), now=NOW)
        store.create_tag(new=NewTag(name="jordan", kind=TagKind.ENTITY, description="tango friend from Blue Note"), now=NOW)
        store.add_alias(alias="jordy", tag="jordan")
        for number in range(facts):
            store.add_fact(detail=f"Jordan fact number {number}", relevance=5, occurred=parse_occurred(text="2026-07-14"), tags=["jordan", "friend"], source_conversation=None, now=NOW)
        bucket = parse_bucket_name(name="2026 Q3")
        assert bucket is not None
        store.set_period(bucket=bucket, summary="Tango summer ☕", now=NOW)


def test_recall_an_entity_by_alias(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    code, out, _ = run_cli(["recall", "Jordy"])
    assert code == 0
    assert out.startswith("jordan (entity): tango friend from Blue Note")
    assert "#1 [5] 2026-07-14 · Jordan fact number 0 (friend, jordan)" in out
    assert "Categories: friend (2)" in out


def test_recall_shows_a_depth_footer_when_facts_are_cut(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths, facts=12)
    _, out, _ = run_cli(["recall", "jordan"])
    assert "2 more facts: .venv/Scripts/python -m memorylayers facts jordan --limit 12 --parent pk" in out


def test_recall_unknown_names_the_nearest(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    code, out, _ = run_cli(["recall", "jordn"])
    assert code == 0
    assert "Nothing called 'jordn'. Closest: jordan" in out


def test_recall_a_period(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    _, out, _ = run_cli(["recall", "--period", "2026 Q3"])
    assert "Tango summer" in out


def test_facts_between(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    _, out, _ = run_cli(["facts", "--between", "2026-07..2026-08", "--limit", "1"])
    assert out.count("Jordan fact number") == 1
    assert "1 more facts:" in out


def test_search_and_listings(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    assert "period: 2026 Q3" in run_cli(["search", "tango"])[1]
    assert "Entities: jordan (2)" in run_cli(["tags"])[1]
    assert "2026 Q3 (quarter)" in run_cli(["periods"])[1]


def test_bad_between_exits_2(paths: ParentPaths, run_cli: Run) -> None:
    _seed(paths)
    code, _, err = run_cli(["facts", "--between", "last summer"])
    assert code == 2
    assert "cannot read" in err


def test_non_ascii_survives_a_pipe(paths: ParentPaths) -> None:
    _seed(paths)
    env = {key: value for key, value in os.environ.items() if key not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    result = subprocess.run([sys.executable, "-m", "memorylayers", "recall", "--period", "2026 Q3", "--parent", "pk"], capture_output=True, cwd=PROJECT_ROOT, env=env, check=False)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert "☕" in result.stdout.decode("utf-8")
