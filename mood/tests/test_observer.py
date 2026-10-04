import json
from datetime import timedelta
from pathlib import Path

import pytest

from mood.adapters.locks import observer_lock_path, try_lock
from mood.adapters.paths import PROMPTS_DIR, mood_paths
from mood.adapters.sessions import load_mood, save_mood
from mood.domain.observer import ObserverReplyError, build_observer_brief, parse_observer_output
from mood.entry import cli
from mood.models.config import MoodConfig
from mood.models.mood import Axis
from mood.models.paths import MoodPaths
from mood.tests.conftest import NOW, mood_state, write_persona, write_transcript
from persona.adapters.files import read_mood_scales
from persona.models import PersonaNames

REPLY = {"deltas": {"playfulness": 2, "irritation": -1}, "presence_delta": 1, "probing": False, "reason": "a joke landed"}


def _envelope(*, text: str, is_error: bool = False) -> str:
    return json.dumps({"type": "result", "subtype": "success", "is_error": is_error, "result": text})


NAMES = PersonaNames(assistant_name="Nova", user_name="Alex")
SCALES = "| Scale | 0 | 10 |\n|---|---|---|\n| cheerfulness | Grey | Sunny |"


def _template() -> str:
    return (PROMPTS_DIR / "observer.md").read_text(encoding="utf-8")


def test_there_are_five_scales() -> None:
    assert [axis.value for axis in Axis] == ["cheerfulness", "playfulness", "irritation", "melancholy", "restlessness"]


def test_the_shipped_persona_describes_every_scale_and_presence() -> None:
    rows = [line.split("|")[1].strip() for line in read_mood_scales().splitlines()[2:]]
    assert rows == [axis.value for axis in Axis] + ["presence"]


def test_the_brief_holds_mood_turns_names_and_scales() -> None:
    brief = build_observer_brief(template=_template(), state=mood_state(melancholy=7), turns="Alex: $5 for a coffee?", names=NAMES, scales=SCALES)
    assert "melancholy 7" in brief and "Alex: $5 for a coffee?" in brief
    assert brief.startswith("You watch a conversation between Alex and Nova,")
    assert SCALES in brief and "$" not in brief.replace("$5", "")


def test_an_unnamed_user_is_the_user() -> None:
    brief = build_observer_brief(template=_template(), state=mood_state(), turns="", names=PersonaNames(assistant_name="Nova"), scales=SCALES)
    assert brief.startswith("You watch a conversation between the user and Nova,")


@pytest.mark.parametrize("user_name", ["O'Brien", "$user ${assistant} $$", "Zoë Ångström"])
def test_awkward_user_names_survive_the_brief(user_name: str) -> None:
    brief = build_observer_brief(template=_template(), state=mood_state(), turns="", names=PersonaNames(assistant_name="Nova", user_name=user_name), scales=SCALES)
    assert brief.startswith(f"You watch a conversation between {user_name} and Nova,")


@pytest.mark.parametrize(
    "text",
    [
        json.dumps(REPLY),
        f"```json\n{json.dumps(REPLY)}\n```",
        f"Here is my judgement:\n{json.dumps(REPLY | {'extra': 'ignored'})}",
    ],
)
def test_replies_parse(text: str) -> None:
    reply = parse_observer_output(output=_envelope(text=text))
    assert reply.deltas == {Axis.PLAYFULNESS: 2, Axis.IRRITATION: -1} and reply.reason == "a joke landed"


@pytest.mark.parametrize(
    "output",
    [
        "not json at all",
        _envelope(text="I cannot judge this."),
        _envelope(text=json.dumps(REPLY), is_error=True),
        _envelope(text=json.dumps(REPLY | {"presence_delta": 4})),
        _envelope(text=json.dumps(REPLY | {"deltas": {"jealousy": 1}})),
    ],
)
def test_bad_replies_are_errors(output: str) -> None:
    with pytest.raises(ObserverReplyError):
        parse_observer_output(output=output)


def _setup(*, tmp_path: Path) -> tuple[MoodPaths, Path]:
    paths = mood_paths(parent="pk")
    save_mood(paths=paths, session_id="s1", state=mood_state(playfulness=4, irritation=3))
    transcript = write_transcript(path=tmp_path / "s1.jsonl", turns=[("user", "knock knock"), ("assistant", "*sighs* who's there")])
    return paths, transcript


def test_observe_applies_a_clamped_reply(tmp_path: Path, data_root: Path) -> None:
    paths, transcript = _setup(tmp_path=tmp_path)
    briefs: list[str] = []

    def call(brief: str) -> str:
        briefs.append(brief)
        return _envelope(text=json.dumps(REPLY))

    cli.observe(paths=paths, session_id="s1", transcript_path=transcript, config=MoodConfig(), call_observer=call, now=lambda: NOW + timedelta(minutes=3))
    state = load_mood(paths=paths, session_id="s1")
    assert state is not None
    assert state.playfulness == pytest.approx(4.5) and state.irritation == pytest.approx(2.5)
    assert "Nova: *sighs* who's there" in briefs[0] and "the user: knock knock" in briefs[0]


def test_observe_takes_names_and_scales_from_a_local_persona(tmp_path: Path, data_root: Path, shipped_persona: Path) -> None:
    write_persona(root=shipped_persona, assistant_name="Iris", user_name="Sam", persona_md=f"# Iris\n\n{SCALES}\n")
    paths, transcript = _setup(tmp_path=tmp_path)
    briefs: list[str] = []

    def call(brief: str) -> str:
        briefs.append(brief)
        return _envelope(text=json.dumps(REPLY))

    cli.observe(paths=paths, session_id="s1", transcript_path=transcript, config=MoodConfig(), call_observer=call, now=lambda: NOW + timedelta(minutes=3))
    assert briefs[0].startswith("You watch a conversation between Sam and Iris,")
    assert "Sam: knock knock" in briefs[0] and "Iris: *sighs* who's there" in briefs[0]
    assert SCALES in briefs[0] and "| playfulness |" not in briefs[0]


def test_a_persona_without_a_scale_table_stops_the_observer_and_names_the_file(tmp_path: Path, data_root: Path, shipped_persona: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local = write_persona(root=shipped_persona, assistant_name="Iris", user_name="Sam", persona_md="# Iris, who forgot her scales\n")
    paths, transcript = _setup(tmp_path=tmp_path)
    monkeypatch.setattr(cli, "find_claude", lambda *, executable: "claude")
    monkeypatch.setattr(cli, "run_observer_claude", lambda **kwargs: pytest.fail("the observer ran without scales"))
    assert cli.main(argv=["observe", "--parent", "pk", "--session", "s1", "--transcript", str(transcript)]) == 1
    log = (paths.logs / "observer.log").read_text(encoding="utf-8")
    assert str(local / "PERSONA.md") in log and "mood-scale table" in log and "Traceback" not in log
    assert load_mood(paths=paths, session_id="s1") == mood_state(playfulness=4, irritation=3)


def test_a_bad_reply_leaves_the_mood(tmp_path: Path, data_root: Path) -> None:
    paths, transcript = _setup(tmp_path=tmp_path)
    with pytest.raises(ObserverReplyError):
        cli.observe(paths=paths, session_id="s1", transcript_path=transcript, config=MoodConfig(), call_observer=lambda brief: "garbage", now=lambda: NOW + timedelta(minutes=3))
    assert load_mood(paths=paths, session_id="s1") == mood_state(playfulness=4, irritation=3)


def test_a_late_reply_does_not_overwrite_a_fresh_roll(tmp_path: Path, data_root: Path) -> None:
    paths, transcript = _setup(tmp_path=tmp_path)
    rerolled = mood_state(melancholy=8).model_copy(update={"rolled_at": NOW + timedelta(minutes=1), "updated_at": NOW + timedelta(minutes=1)})

    def call(brief: str) -> str:
        save_mood(paths=paths, session_id="s1", state=rerolled)  # the user typed /pk again while the observer ran
        return _envelope(text=json.dumps(REPLY))

    cli.observe(paths=paths, session_id="s1", transcript_path=transcript, config=MoodConfig(), call_observer=call, now=lambda: NOW + timedelta(minutes=3))
    assert load_mood(paths=paths, session_id="s1") == rerolled


def test_main_logs_failure_and_releases_the_lock(tmp_path: Path, data_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths, transcript = _setup(tmp_path=tmp_path)
    lock = observer_lock_path(paths=paths, session_id="s1")
    assert try_lock(path=lock, now=NOW, stale_after=timedelta(minutes=5))
    monkeypatch.setattr(cli, "find_claude", lambda *, executable: None)
    assert cli.main(argv=["observe", "--parent", "pk", "--session", "s1", "--transcript", str(transcript)]) == 1
    assert not lock.exists()
    assert "not found" in (paths.logs / "observer.log").read_text(encoding="utf-8")


def test_locks_are_exclusive_until_stale(tmp_path: Path) -> None:
    lock = tmp_path / "locks" / "s1.lock"
    assert try_lock(path=lock, now=NOW, stale_after=timedelta(minutes=5))
    assert not try_lock(path=lock, now=NOW, stale_after=timedelta(minutes=5))
    assert try_lock(path=lock, now=NOW + timedelta(hours=1), stale_after=timedelta(minutes=5))
