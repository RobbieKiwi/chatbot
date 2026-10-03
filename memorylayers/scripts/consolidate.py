"""Tidy the tag vocabulary with a headless consolidator, then rebuild summaries. Run: uv run python -m memorylayers.scripts.consolidate"""

import subprocess

from memorylayers.adapters.paths import PROJECT_ROOT
from memorylayers.adapters.processes import runner_command
from memorylayers.models.vocab import WorkerKind

TIMEOUT_MINUTES = 60


def consolidate(*, parent: str) -> None:
    print("Running the consolidator; its log lands in the parent's logs folder…")
    subprocess.run([*runner_command(parent=parent, kind=WorkerKind.CONSOLIDATOR), "--timeout-minutes", str(TIMEOUT_MINUTES)], cwd=PROJECT_ROOT, check=False)
    print("Rebuilding summaries…")
    subprocess.run([*runner_command(parent=parent, kind=WorkerKind.SUMMARISER), "--timeout-minutes", "120"], cwd=PROJECT_ROOT, check=False)


if __name__ == "__main__":
    consolidate(parent="chatbot")
