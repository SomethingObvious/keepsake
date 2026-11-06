"""Runs `python -m yt_dlp` and `python -m gallery_dl` inside this process.

Keepsake starts both tools as programs and reads what they print, but an Android
app has no Python program to start. Each run here gets a thread and a sink that
looks enough like a pipe for Keepsake's readers, and a handle that looks enough
like a Popen for its queue.
"""

import itertools
import os
import subprocess
import sys
import threading
import traceback
from collections.abc import Callable
from typing import Any

MODULES = ("yt_dlp", "gallery_dl")


class Stopped(BaseException):
    """Raised inside a run that was cancelled, past the tools' own `except Exception`."""


class Sink:
    """Where one run's output goes: a pipe while streaming, or a buffer to hand back."""

    encoding = "utf-8"
    errors = "replace"

    def __init__(self, fd: int | None = None) -> None:
        self.fd = fd
        self.parts: list[str] = []
        self.stopped = False

    def write(self, text: str) -> int:
        if self.stopped:
            raise Stopped
        if self.fd is None:
            self.parts.append(text)
        elif text:
            os.write(self.fd, text.encode("utf-8", "replace"))
        return len(text)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False

    def reconfigure(self, **_: Any) -> None:
        pass

    def text(self) -> str:
        return "".join(self.parts)


class Router:
    """Stands in for sys.stdout or sys.stderr and sends each thread's writes to its own run."""

    def __init__(self, fallback: Any) -> None:
        self.fallback = fallback
        self.sinks: dict[int, Sink] = {}

    def target(self) -> Any:
        return self.sinks.get(threading.get_ident(), self.fallback)

    def write(self, text: str) -> int:
        return self.target().write(text)

    def flush(self) -> None:
        self.target().flush()

    def isatty(self) -> bool:
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self.fallback, name)


OUT, ERR = Router(sys.stdout), Router(sys.stderr)
GALLERY = threading.Lock()  # gallery-dl keeps its settings in globals, so one run at a time
RUNS: dict[int, "Run"] = {}
NUMBERS = itertools.count(1)


def install() -> None:
    """Put the routers in place of the standard streams, once."""
    if sys.stdout is not OUT:
        sys.stdout, sys.stderr = OUT, ERR
        import yt_dlp

        original = yt_dlp.YoutubeDL.__init__

        def init(self: Any, *args: Any, **kwargs: Any) -> None:
            original(self, *args, **kwargs)
            # Fragments download on helper threads, so the sinks go to the instance itself.
            own = {id(OUT): OUT.target(), id(ERR): ERR.target()}
            files = self._out_files
            for name in ("out", "error", "screen", "console"):
                stream = getattr(files, name, None)
                if id(stream) in own:
                    setattr(files, name, own[id(stream)])

        yt_dlp.YoutubeDL.__init__ = init


def handles(command: list[str]) -> bool:
    """Return whether this command is one of the Python tools run in here."""
    return command[1:2] == ["-m"] and command[2:3] != [] and command[2] in MODULES


def exit_code(problem: SystemExit) -> int:
    code = problem.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    print(code, file=sys.stderr)
    return 1


def ytdlp(args: list[str]) -> int:
    import yt_dlp

    try:
        yt_dlp.main(args)
    except SystemExit as done:
        return exit_code(done)
    return 0


def gallery(args: list[str]) -> int:
    import logging

    import gallery_dl
    from gallery_dl import config

    with GALLERY:
        handlers = logging.getLogger().handlers[:]
        before = sys.argv
        sys.argv = ["gallery-dl", *args]
        config.clear()
        try:
            return gallery_dl.main() or 0
        except SystemExit as done:
            return exit_code(done)
        finally:
            sys.argv = before
            logging.getLogger().handlers[:] = handlers


TOOLS: dict[str, Callable[[list[str]], int]] = {"yt_dlp": ytdlp, "gallery_dl": gallery}


class Run:
    """One tool run on its own thread, with the parts of Popen that Keepsake uses."""

    def __init__(self, command: list[str], *, stream: bool) -> None:
        self.args = command
        self.pid = -next(NUMBERS)
        self.returncode: int | None = None
        if stream:
            read, write = os.pipe()
            self.stdout: Any = open(read, encoding="utf-8", errors="replace")
            self.out = self.err = Sink(write)
        else:
            self.stdout = None
            self.out, self.err = Sink(), Sink()
        RUNS[self.pid] = self
        self.thread = threading.Thread(target=self.main, daemon=True, name=command[2])
        self.thread.start()

    def main(self) -> None:
        me = threading.get_ident()
        OUT.sinks[me], ERR.sinks[me] = self.out, self.err
        code = 1
        try:
            code = TOOLS[self.args[2]](self.args[3:])
        except Stopped:
            code = -15
        except BaseException:  # a crashed tool is an exit code, as it would be for a program
            try:
                self.err.write(traceback.format_exc())
            except Stopped:
                pass
        finally:
            OUT.sinks.pop(me, None)
            ERR.sinks.pop(me, None)
            self.returncode = code
            RUNS.pop(self.pid, None)
            if self.out.fd is not None:
                os.close(self.out.fd)

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        self.thread.join(timeout)
        if self.thread.is_alive():
            raise subprocess.TimeoutExpired(self.args, timeout or 0)
        return self.returncode if self.returncode is not None else 1

    def terminate(self) -> None:
        self.out.stopped = self.err.stopped = True

    kill = terminate


def run(command: list[str], timeout: float | None) -> subprocess.CompletedProcess[str]:
    """Run a tool to the end and return what it printed, as subprocess.run would."""
    done = Run(command, stream=False)
    try:
        code = done.wait(timeout)
    except subprocess.TimeoutExpired:
        done.terminate()
        raise
    return subprocess.CompletedProcess(command, code, done.out.text(), done.err.text())


def start(command: list[str]) -> Run:
    """Start a tool whose output is read line by line, as Popen would."""
    return Run(command, stream=True)


def stop(pid: int) -> bool:
    """Cancel a run by the pid it was given, and say whether it was one of these."""
    found = RUNS.get(pid)
    if found:
        found.terminate()
    return found is not None
