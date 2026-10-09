"""Moving in what the app left behind when it was called Siphon.

Its settings, history, sign-ins, text remover and the download folders named
after it move to Keepsake's names on the first start, and every path saved
inside them follows, so nothing is lost or downloaded twice.
"""

import ctypes
import winreg
from pathlib import Path
from typing import cast

from keepsake import APP, paths, store, winapi

OLD = "Siphon"
OLD_KEYS = (r"Software\Classes\siphon", r"Software\Classes\AppUserModelId\Siphon.Downloader")


def folders() -> list[tuple[Path, Path]]:
    """Return each folder named after Siphon, paired with Keepsake's, data folder first."""
    known = [
        winapi.known_folder(winapi.VIDEOS, "Videos"),
        winapi.known_folder(winapi.MUSIC, "Music"),
        winapi.known_folder(winapi.PICTURES, "Pictures"),
        winapi.known_folder(winapi.DOCUMENTS, "Documents"),
    ]
    bases = [paths.DATA.parent, paths.TEXT_REMOVAL.parent.parent, *known]
    return [(base / OLD, base / APP) for base in bases]


def rewritten(value: object, moves: list[tuple[str, str]]) -> object:
    """Return a saved value with every path inside a moved folder pointing into its new one."""
    if isinstance(value, str):
        for old, new in moves:
            low = old.lower()
            if value.lower() == low or value.lower().startswith((low + "\\", low + "/")):
                return new + value[len(old) :]
        return value
    if isinstance(value, list):
        return [rewritten(item, moves) for item in cast("list[object]", value)]
    if isinstance(value, dict):
        pairs = cast("dict[object, object]", value).items()
        return {rewritten(key, moves): rewritten(item, moves) for key, item in pairs}
    return value


def move_in() -> None:
    """Move Siphon's folders to Keepsake's names, once, and the saved paths with them."""
    moves: list[tuple[str, str]] = []
    moved = False
    for old, new in folders():
        if old.is_dir() and not new.exists():
            try:
                old.rename(new)
                moved = True
            except OSError:
                if old == paths.DATA.parent / OLD:
                    # Starting fresh would strand the history and settings, so stop instead.
                    ctypes.WinDLL("user32").MessageBoxW(
                        None, f"Close {OLD} first, then open {APP} again.", APP, 0x10
                    )
                    raise SystemExit(1) from None
        # A folder Siphon never made still has its path in the settings, and thumbnails
        # are saved as file links.
        if not old.exists():
            moves += [(str(old), str(new)), (old.as_uri(), new.as_uri())]
    if not moved:
        return
    for saved in paths.DATA.glob("*.json"):
        value = store.load(saved, None)
        if value is not None and rewritten(value, moves) != value:
            store.save(saved, rewritten(value, moves))
    forget_registry()


def forget_registry() -> None:
    """Remove what Siphon registered: its links, its notification name and its start entry."""
    advapi32 = ctypes.WinDLL("advapi32")
    for key in OLD_KEYS:
        advapi32.RegDeleteTreeW(ctypes.c_void_p(winreg.HKEY_CURRENT_USER), key)
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, winapi.RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as run:
            winreg.DeleteValue(run, OLD)
    except OSError:
        return
