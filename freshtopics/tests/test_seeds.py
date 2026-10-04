import random
import subprocess

import pytest

import freshtopics.__main__
import freshtopics.gap_probe
from freshtopics.__main__ import main
from freshtopics.models import Probe, Seeds
from freshtopics.seeds import choose_seed, draw_seeds, parse_gap_lines, render_seed

WORDS = ["anvil", "kite", "lighthouse", "accordion"]
SUBJECTS = ["mycology", "maritime law"]
PROBE = Probe(tag="acme", text="His days at work are a blank.")


def test_draw_seeds_gives_two_different_words_and_a_subject() -> None:
    seeds = draw_seeds(words=WORDS, subjects=SUBJECTS, rng=random.Random(3))
    assert seeds.words[0] != seeds.words[1]
    assert set(seeds.words) <= set(WORDS) and seeds.subject in SUBJECTS


def test_render() -> None:
    assert render_seed(seed=Seeds(words=("anvil", "kite"), subject="mycology")) == "seeds: anvil · kite · mycology"
    assert render_seed(seed=PROBE) == "probe: acme: His days at work are a blank."


def test_parse_gap_lines() -> None:
    assert parse_gap_lines(output="acme: His days at work are a blank.\n\nnot a gap line\nlisbon: Named: never described.\n") == [PROBE, Probe(tag="lisbon", text="Named: never described.")]


def test_a_probe_when_the_dice_say_so() -> None:
    assert choose_seed(probe_chance=1.0, rng=random.Random(0), list_gaps=lambda: [PROBE], words=WORDS, subjects=SUBJECTS) == PROBE


def test_no_gaps_fall_through_to_seeds() -> None:
    assert isinstance(choose_seed(probe_chance=1.0, rng=random.Random(0), list_gaps=list, words=WORDS, subjects=SUBJECTS), Seeds)


def test_gaps_are_not_asked_for_when_the_dice_say_seeds() -> None:
    def fail() -> list[Probe]:
        raise AssertionError("gaps asked for")

    assert isinstance(choose_seed(probe_chance=0.0, rng=random.Random(0), list_gaps=fail, words=WORDS, subjects=SUBJECTS), Seeds)


def test_the_probe_chance_is_honoured() -> None:
    rng = random.Random(5)
    probes = sum(isinstance(choose_seed(probe_chance=0.25, rng=rng, list_gaps=lambda: [PROBE], words=WORDS, subjects=SUBJECTS), Probe) for _ in range(4000))
    assert 900 < probes < 1100


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired(cmd="x", timeout=1), FileNotFoundError("python")])
def test_a_failing_gap_call_gives_no_gaps(monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    def run(*args: object, **kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(freshtopics.gap_probe.subprocess, "run", run)
    assert freshtopics.gap_probe.list_available_gaps(parent="pk") == []


def test_a_nonzero_exit_gives_no_gaps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(freshtopics.gap_probe.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args=[], returncode=2, stdout="acme: x", stderr="boom"))
    assert freshtopics.gap_probe.list_available_gaps(parent="pk") == []


def test_cli_seeds(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(freshtopics.__main__, "list_available_gaps", lambda *, parent: [PROBE])
    assert main(argv=["seeds", "--parent", "pk", "--probe-chance", "0"]) == 0
    words = capsys.readouterr().out.strip().removeprefix("seeds: ").split(" · ")
    assert len(words) == 3
    assert main(argv=["seeds", "--parent", "pk", "--probe-chance", "1"]) == 0
    assert capsys.readouterr().out.strip() == "probe: acme: His days at work are a blank."
