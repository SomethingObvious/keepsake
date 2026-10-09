"""Running other programs without a console window flashing up."""

import os
import subprocess
from pathlib import Path

from keepsake import paths

NO_WINDOW = subprocess.CREATE_NO_WINDOW
# Downloads, conversions and the text remover run beneath whatever the person
# is doing, so a slow computer stays usable while they work. What they start
# inherits it: ffmpeg under yt-dlp, and the judge's server under the remover.
BACKGROUND = NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
# UTF-8 both ways: a title in Japanese or a filename with an emoji has to
# survive the trip through a pipe.
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def run(command: list[str], timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    """Run a program to completion and return what it printed."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENV,
        creationflags=NO_WINDOW,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def first_line(command: list[str]) -> str | None:
    """Return the first line a program prints on success, or None."""
    try:
        result = run(command, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = result.stdout.strip().splitlines()
    return lines[0] if result.returncode == 0 and lines else None


def stream(command: list[str], cwd: Path | None = None) -> subprocess.Popen[str]:
    """Start a program whose output is read line by line as it arrives."""
    return subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        env=ENV,
        creationflags=BACKGROUND,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )


def detach(command: list[str], cwd: str | None = None) -> None:
    """Start a program that outlives this one."""
    subprocess.Popen(
        command,
        cwd=cwd,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )


def open_with_windows(target: str | Path) -> None:
    """Open a file, a folder or a web page with whatever Windows opens it with."""
    detach([paths.tool("explorer"), str(target)])


def kill_tree(pid: int) -> None:
    """End a process and everything it started: yt-dlp leaves ffmpeg running otherwise."""
    run([paths.tool("taskkill"), "/T", "/F", "/PID", str(pid)])


def git(*args: str, timeout: float = 120) -> subprocess.CompletedProcess[str]:
    """Run git in Keepsake's own folder, failing rather than waiting on a prompt nobody can see."""
    return subprocess.run(
        [paths.tool("git"), "-C", str(paths.ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**ENV, "GIT_TERMINAL_PROMPT": "0"},
        creationflags=NO_WINDOW,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        check=False,
    )
