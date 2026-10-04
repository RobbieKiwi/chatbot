"""Operating-system processes: finding claude, detached launches and the observer's headless run."""

import shutil
import subprocess
import sys
from pathlib import Path


def find_claude(*, executable: str) -> Path | None:
    # On Windows an npm install is a .cmd shim that subprocess cannot start by bare name.
    found = shutil.which(executable)
    return Path(found) if found else None


def spawn_detached(*, args: list[str], cwd: Path, log_path: Path) -> None:
    """Start a process that outlives this one: no console, its own process group."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        if sys.platform != "win32":
            subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True, start_new_session=True)
            return
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        try:
            # Leave the hook's job object, so the observer survives Claude Code reaping the hook.
            subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB)
        except OSError:  # the job forbids breakaway
            subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True, creationflags=flags)


def run_observer_claude(*, claude: Path, model: str, brief: str, timeout_s: float, cwd: Path) -> str:
    """One headless claude run with no tools over the brief; its JSON envelope."""
    command = [str(claude), "-p", "--model", model, "--output-format", "json", "--no-session-persistence", "--tools", ""]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    result = subprocess.run(command, cwd=cwd, input=brief, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout_s, creationflags=flags, check=False)
    return result.stdout
