r"""Install Keepsake for this user, or bring an installed copy up to the newest release.

    python scripts/install.py

1. Clones this repository's origin into %LOCALAPPDATA%\\Programs\\Keepsake (or
    fetches, if it is already there) and checks out main, where every commit
    is a release.
    That copy updates itself from then on; this folder is left for working in.
2. Installs what it needs with pip.
3. Registers keepsake:// links, which the browser bookmarklets open.
4. Puts Keepsake on the desktop and in the Start menu. Each shortcut carries the
    app id the window runs under, so a pinned taskbar button is Keepsake and not
    Python, and relaunches Keepsake rather than a bare interpreter.
"""

import ctypes
import os
import shutil
import struct
import subprocess
import sys
import uuid
import winreg
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Keepsake"
APP_ID = "Keepsake.Downloader"
PYTHONW = str(Path(sys.executable).with_name("pythonw.exe"))
# PKEY_AppUserModel_ID, and the interface that sets it.
APP_ID_KEY = uuid.UUID("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3").bytes_le + struct.pack("<I", 5)
PROPERTY_STORE = uuid.UUID("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99").bytes_le
GPS_READWRITE = 2
VT_LPWSTR = 31
SET_VALUE, COMMIT, RELEASE = 6, 7, 2  # IPropertyStore's methods, by place in its table


def run(*command: str, cwd: Path | None = None) -> str:
    """Run a program, stop on failure, and return what it printed."""
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        message = f"{' '.join(command[:3])} failed:\n{result.stderr.strip()}"
        raise SystemExit(message)
    return result.stdout.strip()


def git() -> str:
    """Return the git program."""
    found = shutil.which("git")
    if not found:
        message = "git is needed to install Keepsake"
        raise SystemExit(message)
    return found


def fetch_copy() -> None:
    """Make the installed copy exist, at the newest release."""
    origin = run(git(), "-C", str(ROOT), "remote", "get-url", "origin")
    if (INSTALL / ".git").is_dir():
        run(git(), "-C", str(INSTALL), "fetch", "--quiet", "origin", "main")
    else:
        INSTALL.parent.mkdir(parents=True, exist_ok=True)
        run(git(), "clone", "--quiet", origin, str(INSTALL))
    run(git(), "-C", str(INSTALL), "checkout", "--quiet", "--detach", "origin/main")
    sys.stdout.write(f"Keepsake is at origin/main in {INSTALL}\n")


def requirements() -> None:
    """Install what the installed copy needs."""
    run(
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--disable-pip-version-check",
        "-r",
        str(INSTALL / "requirements.txt"),
    )


def launch_command(*extra: str) -> str:
    """Return the command that opens the installed Keepsake."""
    return f'"{PYTHONW}" "{INSTALL / "launch.pyw"}"' + "".join(f" {part}" for part in extra)


def register_links() -> None:
    """Make keepsake://add?url=... open the installed Keepsake."""
    base = r"Software\Classes\keepsake"
    for key, name, value in (
        (base, "", "URL:Keepsake"),
        (base, "URL Protocol", ""),
        (base + r"\DefaultIcon", "", str(INSTALL / "assets" / "keepsake.ico")),
        (base + r"\shell\open\command", "", launch_command('"%1"')),
    ):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
            winreg.SetValueEx(handle, name, 0, winreg.REG_SZ, value)


def register_identity() -> None:
    """Have notifications say "Keepsake" with its logo, rather than the bare app id."""
    key = rf"Software\Classes\AppUserModelId\{APP_ID}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
        winreg.SetValueEx(handle, "DisplayName", 0, winreg.REG_SZ, "Keepsake")
        winreg.SetValueEx(
            handle, "IconUri", 0, winreg.REG_SZ, str(INSTALL / "assets" / "keepsake.png")
        )


def shortcut(where: Path) -> None:
    """Write a shortcut to the installed Keepsake, carrying its app id."""
    where.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:TARGET_LNK);"
        "$s.TargetPath = $env:TARGET_EXE; $s.Arguments = $env:TARGET_ARGS;"
        "$s.WorkingDirectory = $env:TARGET_DIR; $s.IconLocation = $env:TARGET_ICON;"
        "$s.Description = 'Download video, audio and galleries'; $s.Save()"
    )
    environment = {
        **os.environ,
        "TARGET_LNK": str(where),
        "TARGET_EXE": PYTHONW,
        "TARGET_ARGS": f'"{INSTALL / "launch.pyw"}"',
        "TARGET_DIR": str(INSTALL),
        "TARGET_ICON": f"{INSTALL / 'assets' / 'keepsake.ico'},0",
    }
    powershell = shutil.which("powershell") or "powershell"
    subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        env=environment,
        check=True,
        capture_output=True,
    )
    set_app_id(where)


def set_app_id(path: Path) -> None:
    """Write the app id into a shortcut's properties, through its property store."""
    ole32, shell32 = ctypes.WinDLL("ole32"), ctypes.WinDLL("shell32")
    ole32.CoInitialize(None)
    store = ctypes.c_void_p()
    interface = ctypes.create_string_buffer(PROPERTY_STORE, len(PROPERTY_STORE))
    status = shell32.SHGetPropertyStoreFromParsingName(
        str(path),
        None,
        GPS_READWRITE,
        interface,
        ctypes.byref(store),
    )
    if status or not store.value:
        message = f"could not open the properties of {path}"
        raise SystemExit(message)
    table = ctypes.cast(store, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    method = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    text = ctypes.create_unicode_buffer(APP_ID)
    # A PROPVARIANT holding a wide string: its type, then a pointer to the text.
    packed = struct.pack("<H6xQ8x", VT_LPWSTR, ctypes.addressof(text))
    value = ctypes.create_string_buffer(packed, len(packed))
    key = ctypes.create_string_buffer(APP_ID_KEY, len(APP_ID_KEY))
    method(table[SET_VALUE])(store, key, value)
    ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p)(table[COMMIT])(store)
    ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)(table[RELEASE])(store)


def main() -> None:
    """Install, then say where everything went."""
    fetch_copy()
    requirements()
    register_links()
    register_identity()
    desktop = Path(os.environ["USERPROFILE"]) / "Desktop" / "Keepsake.lnk"
    menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    # The app was called Siphon. Renaming its shortcut keeps the icon where it sat on the
    # desktop, where a new one would land at the bottom of a full desktop and go unseen.
    if (old := desktop.with_name("Siphon.lnk")).exists() and not desktop.exists():
        old.rename(desktop)
    (menu / "Siphon.lnk").unlink(missing_ok=True)
    for where in (desktop, menu / "Keepsake.lnk"):
        shortcut(where)
        sys.stdout.write(f"Shortcut: {where}\n")


if __name__ == "__main__":
    main()
