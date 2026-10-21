"""Where everything lives on this machine.

Modules read these as `paths.DATA` at call time rather than importing the
names, so a test can point the whole program at a scratch folder.
"""

import os
import shutil
import sys
from pathlib import Path

from keepsake import APP

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui"
ICON = ROOT / "assets" / "keepsake.ico"
LOGO = ROOT / "assets" / "keepsake.png"
# A copy from the installer keeps the app in app\ beside its own Python, and starts
# through keepsake.pyw, which puts a downloaded update in place first.
PACKAGED = (ROOT.parent / "keepsake.pyw").is_file() and (ROOT.parent / "python").is_dir()
LAUNCHER = ROOT.parent / "keepsake.pyw" if PACKAGED else ROOT / "launch.pyw"

DATA = Path(os.environ.get("APPDATA") or Path.home()) / APP
# The copy on the desktop runs from here and updates itself to each release;
# any other checkout is somebody working on it, and is left alone.
INSTALL = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / APP
AFTERIMAGE = Path(os.environ.get("LOCALAPPDATA", "")) / "afterimage" / "afterimage-app.exe"
# Remove Text's models: downloads, so local, not roaming.
TEXT_REMOVAL = Path(os.environ.get("LOCALAPPDATA", "")) / APP / "text-removal"
# FFmpeg and Deno when Keepsake fetched them, found like any program on the PATH,
# by Keepsake and by everything it runs.
TOOLS = Path(os.environ.get("LOCALAPPDATA", "")) / APP / "tools"
os.environ["PATH"] = os.pathsep.join([str(TOOLS), os.environ.get("PATH", "")])

# Not pythonw for the tools: they print what they wrote, and pythonw has
# nowhere to print it.
PYTHON = str(Path(sys.executable).with_name("python.exe"))
PYTHONW = str(Path(sys.executable).with_name("pythonw.exe"))


def tool(name: str) -> str:
    """Return the full path of a program on PATH, or its bare name if absent."""
    return shutil.which(name) or name
