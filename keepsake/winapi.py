"""The Windows calls Keepsake needs, each behind a small typed function."""

import ctypes
import struct
import threading
import uuid
import winreg
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path

from keepsake import APP, paths

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")
ole32 = ctypes.WinDLL("ole32")
comctl32 = ctypes.WinDLL("comctl32")

SUBCLASSPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    ctypes.c_size_t,
    ctypes.c_size_t,
)
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND,
    SUBCLASSPROC,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
comctl32.DefSubclassProc.restype = ctypes.c_ssize_t
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.IsZoomed.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]

shell32.SHGetKnownFolderPath.argtypes = [
    ctypes.c_char_p,
    wintypes.DWORD,
    wintypes.HANDLE,
    ctypes.POINTER(ctypes.c_wchar_p),
]
shell32.ILCreateFromPathW.restype = ctypes.c_void_p
shell32.ILCreateFromPathW.argtypes = [wintypes.LPCWSTR]
shell32.SHOpenFolderAndSelectItems.argtypes = [
    ctypes.c_void_p,
    wintypes.UINT,
    ctypes.c_void_p,
    wintypes.DWORD,
]
shell32.ILFree.argtypes = [ctypes.c_void_p]
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]

user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.LoadImageW.restype = wintypes.HANDLE
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.OpenProcess.restype = wintypes.HANDLE

CF_UNICODETEXT = 13
COINIT_APARTMENTTHREADED = 0x2
# Windows' own folder for each kind of thing, wherever the user has moved it.
VIDEOS = "18989B1D-99B5-455B-841C-AB7C74E4DDFC"
MUSIC = "4BD8D571-6D19-48D3-BE97-422220080E43"
PICTURES = "33E28130-4E1E-4676-835A-98395C3BC3BB"
DOCUMENTS = "FDD39AD0-238F-46AF-ADB4-6C85480369C7"
ERROR_ALREADY_EXISTS = 183
SYNCHRONIZE = 0x00100000
SW_RESTORE = 9
WM_SETICON = 0x0080
WM_HOTKEY = 0x0312
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x10
MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x1, 0x2, 0x4000
DWM_DARK, DWM_BORDER = 20, 34
EDGE = 0x333333
WM_NCCALCSIZE = 0x0083
WM_WINDOWPOSCHANGING, WM_WINDOWPOSCHANGED = 0x0046, 0x0047
SWP_NOSIZE, SWP_NOMOVE = 0x0001, 0x0002
WINDOWPOS_FLAGS = struct.calcsize("<2Q4i")  # past the two handles and x, y, cx, cy
WM_SYSCOMMAND = 0x0112
SC_MINIMIZE, SC_MAXIMIZE, SC_CLOSE, SC_RESTORE = 0xF020, 0xF030, 0xF060, 0xF120
SWP_FRAME_ONLY = 0x0037  # FRAMECHANGED, and no move, size, z-order or activation


def known_folder(guid: str, fallback: str) -> Path:
    """Return one of Windows' own folders, such as Videos, wherever it has been moved to."""
    found = ctypes.c_wchar_p()
    if shell32.SHGetKnownFolderPath(uuid.UUID(guid).bytes_le, 0, None, ctypes.byref(found)):
        return Path.home() / fallback
    try:
        return Path(found.value or Path.home() / fallback)
    finally:
        ole32.CoTaskMemFree(ctypes.cast(found, ctypes.c_void_p))


def show_in_folder(path: Path) -> bool:
    """Open a file's folder in Explorer with the file selected, as browsers do.

    Not `explorer /select,...`: Python quotes the whole switch when the path has
    a space, and Explorer then opens Documents instead (measured, it was the bug).
    """
    ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)  # this thread may not have COM yet
    item = shell32.ILCreateFromPathW(str(path))
    if not item:
        return False
    try:
        return int(shell32.SHOpenFolderAndSelectItems(item, 0, None, 0)) == 0
    finally:
        shell32.ILFree(item)


def clipboard_text() -> str:
    """Return the text on the clipboard, or an empty string."""
    if not user32.OpenClipboard(None):
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        pointer = kernel32.GlobalLock(handle)
        try:
            return ctypes.wstring_at(pointer) if pointer else ""
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


GMEM_MOVEABLE = 0x0002
kernel32.GlobalAlloc.restype = wintypes.HANDLE
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]


def set_clipboard_text(text: str) -> bool:
    """Put text on the clipboard; return whether it got there."""
    data = ctypes.create_unicode_buffer(text)
    size = ctypes.sizeof(data)
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
    pointer = kernel32.GlobalLock(handle) if handle else None
    if not pointer:
        return False
    ctypes.memmove(pointer, data, size)
    kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        return bool(user32.SetClipboardData(CF_UNICODETEXT, handle))
    finally:
        user32.CloseClipboard()


def clipboard_serial() -> int:
    """Return a number that changes whenever anything is copied."""
    return int(user32.GetClipboardSequenceNumber())


FO_DELETE = 3
# hwnd, wFunc, pFrom, pTo, fFlags, fAnyOperationsAborted, hNameMappings, lpszProgressTitle
FILE_OPERATION = "<QI4xQQH2xIQQ"
FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 0x4, 0x10, 0x40, 0x400


def recycle(path: Path) -> bool:
    """Move a file to the Recycle Bin, so a wrong click is recoverable."""
    # SHFILEOPSTRUCTW as 64-bit Windows lays it out. The path list ends in two
    # NULs: the one added here and the one every buffer carries.
    source = ctypes.create_unicode_buffer(str(path) + "\0")
    flags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    packed = struct.pack(FILE_OPERATION, 0, FO_DELETE, ctypes.addressof(source), 0, flags, 0, 0, 0)
    block = ctypes.create_string_buffer(packed, len(packed))
    return int(shell32.SHFileOperationW(block)) == 0 and not path.exists()


FLASHW_ALL, FLASHW_TIMERNOFG = 3, 12
# cbSize, hwnd, dwFlags, uCount, dwTimeout
FLASH_INFO = "<I4xQIII4x"


def flash(hwnd: int) -> None:
    """Flash a window's taskbar button until it is looked at."""
    size = struct.calcsize(FLASH_INFO)
    packed = struct.pack(FLASH_INFO, size, hwnd, FLASHW_ALL | FLASHW_TIMERNOFG, 0, 0)
    user32.FlashWindowEx(ctypes.create_string_buffer(packed, size))


def in_front(hwnd: int) -> bool:
    """Return whether the window is the one the user is looking at."""
    return int(user32.GetForegroundWindow() or 0) == hwnd


def bring_forward(hwnd: int) -> None:
    """Restore a window and put it in front."""
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)


def dress(hwnd: int, icon: Path) -> None:
    """Give a window the dark frame and Keepsake's icon."""
    for attribute, value in ((DWM_DARK, 1), (DWM_BORDER, EDGE)):
        number = ctypes.c_int(value)
        dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            attribute,
            ctypes.byref(number),
            ctypes.sizeof(number),
        )
    if icon.is_file():
        for which, size in ((1, 32), (0, 16)):  # ICON_BIG, ICON_SMALL
            handle = user32.LoadImageW(None, str(icon), IMAGE_ICON, size, size, LR_LOADFROMFILE)
            if handle:
                user32.SendMessageW(wintypes.HWND(hwnd), WM_SETICON, which, handle)


def _without_caption(
    hwnd: int | None, message: int, wparam: int, lparam: int, _id: int, _data: int
) -> int:
    """Let Windows lay out the frame, then give the caption's rows to the page."""
    if message == WM_NCCALCSIZE and wparam:
        client = wintypes.RECT.from_address(lparam)
        top, left = client.top, client.left
        result = int(comctl32.DefSubclassProc(hwnd, message, wparam, lparam))
        # Maximized, the frame hangs off the screen on every side, so the top
        # comes in by as much as the left did.
        client.top = top + (client.left - left if user32.IsZoomed(hwnd) else 0)
        return result
    if message == WM_WINDOWPOSCHANGING and _FRAME["restoring"]:
        # Windows has already put the window back as it was. WinForms then
        # makes it taller by the caption it thinks is still there, every time.
        ctypes.c_uint.from_address(lparam + WINDOWPOS_FLAGS).value |= SWP_NOSIZE | SWP_NOMOVE
    if message == WM_WINDOWPOSCHANGED:
        normal = not (user32.IsZoomed(hwnd) or user32.IsIconic(hwnd))
        _FRAME["restoring"] = normal and not _FRAME["normal"]
        _FRAME["normal"] = normal
        try:
            return int(comctl32.DefSubclassProc(hwnd, message, wparam, lparam))
        finally:
            _FRAME["restoring"] = False
    return int(comctl32.DefSubclassProc(hwnd, message, wparam, lparam))


_WITHOUT_CAPTION = SUBCLASSPROC(_without_caption)
_FRAME = {"normal": True, "restoring": False}


def drop_caption(hwnd: int) -> None:
    """Take the title bar off a window, keeping the frame that resizes and snaps it.

    Only the thread that made the window can do this.
    """
    comctl32.SetWindowSubclass(hwnd, _WITHOUT_CAPTION, 1, 0)
    user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_FRAME_ONLY)


def maximized(hwnd: int) -> bool:
    """Return whether a window is maximized."""
    return bool(user32.IsZoomed(hwnd))


def window_command(hwnd: int, name: str) -> None:
    """Minimize, maximize or restore, or close a window, as its own title bar would."""
    if name == "maximize":
        code = SC_RESTORE if maximized(hwnd) else SC_MAXIMIZE
    else:
        code = {"minimize": SC_MINIMIZE, "close": SC_CLOSE}.get(name, 0)
    if code:
        user32.PostMessageW(hwnd, WM_SYSCOMMAND, code, 0)


def claim_instance() -> bool:
    """Return whether this is the only Keepsake running, holding the claim until exit."""
    handle = kernel32.CreateMutexW(None, 0, "Local\\Keepsake.Downloader")
    _CLAIM.append(int(handle or 0))
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


_CLAIM: list[int] = []


def wait_for_exit(pid: int, seconds: float = 20) -> None:
    """Wait for another process to end, for a restart that must not overlap."""
    handle = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)
    if handle:
        kernel32.WaitForSingleObject(handle, int(seconds * 1000))
        kernel32.CloseHandle(handle)


APP_ID = "Keepsake.Downloader"


def set_app_id() -> None:
    """Give Keepsake its own taskbar button and icon, rather than Python's."""
    shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)


def register_identity(logo: Path) -> None:
    """Have notifications say "Keepsake" with its logo, rather than the bare app id."""
    key = rf"Software\Classes\AppUserModelId\{APP_ID}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
        winreg.SetValueEx(handle, "DisplayName", 0, winreg.REG_SZ, APP)
        winreg.SetValueEx(handle, "IconUri", 0, winreg.REG_SZ, str(logo))


def launch_command(*extra: str) -> str:
    """Return the command that opens Keepsake, for the registry."""
    return f'"{paths.PYTHONW}" "{paths.LAUNCHER}"' + "".join(f" {part}" for part in extra)


def register_protocol() -> None:
    """Make keepsake://add?url=... open Keepsake, which is what the bookmarklets use."""
    base = r"Software\Classes\keepsake"
    values = (
        (base, "", "URL:Keepsake"),
        (base, "URL Protocol", ""),
        (base + r"\DefaultIcon", "", str(paths.ICON)),
        (base + r"\shell\open\command", "", launch_command('"%1"')),
    )
    for key, name, value in values:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
            winreg.SetValueEx(handle, name, 0, winreg.REG_SZ, value)


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def set_autostart(*, enabled: bool) -> None:
    """Start Keepsake, in the tray, when Windows starts; or stop doing so."""
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as handle:
        if enabled:
            winreg.SetValueEx(handle, APP, 0, winreg.REG_SZ, launch_command("--tray"))
            return
        try:
            winreg.DeleteValue(handle, APP)
        except FileNotFoundError:
            return


VK_D = 0x44


def listen_for_hotkey(pressed: Callable[[], None], enabled: Callable[[], bool]) -> None:
    """Call `pressed` whenever Ctrl+Alt+D is pressed anywhere, from a thread of its own.

    A hotkey belongs to the thread that registered it, so registering and the
    message loop that receives it have to live in the same thread.
    """

    def loop() -> None:
        if not user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_D):
            return  # something else already owns the combination
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if message.message == WM_HOTKEY and enabled():
                pressed()

    threading.Thread(target=loop, daemon=True, name="hotkey").start()
