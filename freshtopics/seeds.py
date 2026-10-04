"""Where a new topic starts: a gap in memory to probe, or random seeds."""

from collections.abc import Callable
from random import Random

from freshtopics.models import Probe, Seeds


def draw_seeds(*, words: list[str], subjects: list[str], rng: Random) -> Seeds:
    first, second = rng.sample(words, 2)
    return Seeds(words=(first, second), subject=rng.choice(subjects))


def parse_gap_lines(*, output: str) -> list[Probe]:
    """Lines of `tag: text`, as memorylayers' `gaps list` prints them."""
    probes = []
    for line in output.splitlines():
        tag, separator, text = line.partition(": ")
        if separator and tag.strip() and text.strip():
            probes.append(Probe(tag=tag.strip(), text=text.strip()))
    return probes


def choose_seed(*, probe_chance: float, rng: Random, list_gaps: Callable[[], list[Probe]], words: list[str], subjects: list[str]) -> Seeds | Probe:
    if rng.random() < probe_chance:
        probes = list_gaps()
        if probes:
            return rng.choice(probes)
    return draw_seeds(words=words, subjects=subjects, rng=rng)


def render_seed(*, seed: Seeds | Probe) -> str:
    if isinstance(seed, Probe):
        return f"probe: {seed.tag}: {seed.text}"
    return f"seeds: {seed.words[0]} · {seed.words[1]} · {seed.subject}"
