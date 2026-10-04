"""The bundled lists that topic seeds are drawn from."""

from pathlib import Path

WORD_LISTS_DIR = Path(__file__).parent / "resources"


def read_word_list(*, name: str) -> list[str]:
    lines = (WORD_LISTS_DIR / name).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]
