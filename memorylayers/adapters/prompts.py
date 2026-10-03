"""Brief templates and the parent's memory guide."""

from memorylayers.adapters.paths import PROMPTS_DIR
from memorylayers.models.paths import ParentPaths


def load_prompt(*, name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def load_memory_guide(*, paths: ParentPaths) -> str:
    try:
        return paths.memory_guide.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "(this parent has no memory guide)"
