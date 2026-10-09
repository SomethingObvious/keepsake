"""Start the installed Keepsake, first putting a downloaded update in its place.

The installer puts this file beside python\\ and app\\. An update arrives as
app.next, and only here, before anything of the app is loaded, is it safe to
swap in. If the new version needs different packages, pip installs them first.
"""

import ctypes
import os
import runpy
import site
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NO_WINDOW = 0x08000000
SYNCHRONIZE = 0x00100000
WAIT_SECONDS = 20


def wait_for_exit(arguments: list[str]) -> None:
    """Let a closing copy finish first, so its files are free to replace."""
    if "--after" not in arguments:
        return
    at = arguments.index("--after")
    kernel32 = ctypes.WinDLL("kernel32")
    handle = kernel32.OpenProcess(SYNCHRONIZE, 0, int(arguments[at + 1]))
    if handle:
        kernel32.WaitForSingleObject(handle, WAIT_SECONDS * 1000)
        kernel32.CloseHandle(handle)


def swap_in_update(here: Path) -> bool:
    """Put app.next in app's place, keeping the old app if anything goes wrong."""
    app, new, old = here / "app", here / "app.next", here / "app.old"
    if not (new / "keepsake" / "__init__.py").is_file():
        return False
    shutil.rmtree(old, ignore_errors=True)
    try:
        app.rename(old)
    except OSError:
        return False
    try:
        new.rename(app)
    except OSError:
        old.rename(app)
        return False
    shutil.rmtree(old, ignore_errors=True)
    return True


def requirements(app: Path) -> str:
    """Return what an app says it needs from pip."""
    listed = app / "requirements.txt"
    return listed.read_text(encoding="utf-8") if listed.is_file() else ""


def own_packages_only() -> None:
    """Use this install's packages and never the ones another Python left in the user's folder.

    The children Keepsake starts (yt-dlp, pip) inherit this.
    """
    os.environ["PYTHONNOUSERSITE"] = "1"
    user = os.path.normcase(site.getusersitepackages())
    sys.path[:] = [entry for entry in sys.path if os.path.normcase(entry) != user]


def main() -> None:
    """Wait, update, then run the app as if it had been started directly."""
    own_packages_only()
    wait_for_exit(sys.argv[1:])
    needed = requirements(HERE / "app")
    if swap_in_update(HERE) and requirements(HERE / "app") != needed:
        python = HERE / "python" / "python.exe"
        listed = HERE / "app" / "requirements.txt"
        command = [str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", str(listed)]
        subprocess.run(command, check=False, creationflags=NO_WINDOW)
    sys.path.insert(0, str(HERE / "app"))
    runpy.run_path(str(HERE / "app" / "launch.pyw"), run_name="__main__")


if __name__ == "__main__":
    main()
