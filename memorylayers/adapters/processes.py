"""Operating-system processes: liveness checks, detached launches and headless claude runs."""

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

from memorylayers.models.vocab import WorkerKind

_STILL_ACTIVE = 259
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def pid_alive(*, pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        # os.kill(pid, 0) would terminate the process on Windows.
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


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
            # Leave the hook's job object, so the worker survives Claude Code reaping the hook.
            subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB)
        except OSError:  # the job forbids breakaway
            subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True, creationflags=flags)


def run_claude(*, claude: Path, model: str, allowed_tools: list[str], brief_path: Path, log_path: Path, timeout_s: float, cwd: Path) -> int:
    """Run one headless claude session over a brief and wait for it."""
    command = [str(claude), "-p", "--model", model, "--no-session-persistence", "--permission-mode", "default"]
    if allowed_tools:
        command += ["--allowedTools", *allowed_tools]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with brief_path.open("rb") as brief, log_path.open("ab") as log:
        result = subprocess.run(command, cwd=cwd, stdin=brief, stdout=log, stderr=subprocess.STDOUT, timeout=timeout_s, creationflags=flags, check=False)
    return result.returncode


def runner_command(*, parent: str, kind: WorkerKind, conversation_id: str | None = None, catch_up: bool = False) -> list[str]:
    command = [sys.executable, "-m", "memorylayers.entry.runner", "--parent", parent, "--kind", kind.value]
    if conversation_id:
        command += ["--conversation", conversation_id]
    if catch_up:
        command.append("--catch-up")
    return command
