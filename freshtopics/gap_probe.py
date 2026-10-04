"""Gaps in memory, asked of memorylayers through its command line like any other agent."""

import os
import subprocess
import sys
from pathlib import Path

from freshtopics.models import Probe
from freshtopics.seeds import parse_gap_lines

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GAP_TIMEOUT_S = 20


def list_available_gaps(*, parent: str) -> list[Probe]:
    """Gaps outside their cooldown; none when memorylayers fails for any reason."""
    command = [sys.executable, "-m", "memorylayers", "gaps", "list", "--available", "--parent", parent]
    try:
        result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=GAP_TIMEOUT_S, check=False, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return parse_gap_lines(output=result.stdout)
