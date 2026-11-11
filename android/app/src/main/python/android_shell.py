"""Runs Keepsake's own Python on Android, with its Windows parts swapped for the phone's.

Kotlin calls start() once and call() for each request the window makes, the
way pywebview would on Windows. The stand-ins go in before Keepsake is imported,
because its modules read Windows' folders and constants at import time.
"""

import json
import os
import subprocess
import sys
import threading
import traceback
import types
import urllib.request
from enum import Enum
from pathlib import Path
from typing import Any

from java import jclass

PLATFORM = jclass("com.somethingobvious.keepsake.Platform")
READY = threading.Event()
STATE: dict[str, Any] = {}


class Anything:
    """Takes any call or attribute, for the tray and window classes a phone never shows."""

    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def __call__(self, *_: Any, **__: Any) -> "Anything":
        return self

    def __getattr__(self, _: str) -> "Anything":
        return Anything()


def module(name: str, **names: Any) -> types.ModuleType:
    made = types.ModuleType(name)
    made.__dict__.update(names)
    made.__getattr__ = lambda _: Anything()
    sys.modules[name] = made
    return made


class FileDialog(Enum):
    OPEN = 10
    FOLDER = 20
    SAVE = 30


class Window:
    """The parts of pywebview's window that Keepsake calls, done the Android way."""

    native = None

    def create_file_dialog(self, kind: FileDialog, directory: str = "", save_filename: str = "", **_: Any) -> tuple[str, ...] | None:
        if kind is FileDialog.FOLDER:
            chosen = PLATFORM.pickFolder(directory)
        elif kind is FileDialog.OPEN:
            chosen = PLATFORM.pickFile()
        else:
            # A phone has no save dialog worth the name, so exports go to Downloads.
            chosen = str(Path(STATE["storage"]) / "Download" / save_filename)
            PLATFORM.toast(f"Saved to Download as {save_filename}")
        return (str(chosen),) if chosen else None

    def show(self) -> None:
        pass

    restore = destroy = minimize = show

    def set_title(self, _: str) -> None:
        pass


def stand_ins() -> None:
    """Put the Windows-only modules' places, so Keepsake imports cleanly."""
    module("winsound", MessageBeep=lambda *_: None, MB_OK=0, MB_ICONHAND=0x10)
    module("winreg")
    module("pystray", Icon=Anything, Menu=Anything, MenuItem=Anything)
    module(
        "webview",
        Window=Window,
        FileDialog=FileDialog,
        create_window=lambda *_, **__: Window(),
        start=lambda *_, **__: None,
        windows=[],
    )
    for name in ("CREATE_NO_WINDOW", "BELOW_NORMAL_PRIORITY_CLASS", "DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
        if not hasattr(subprocess, name):
            setattr(subprocess, name, 0)


FOLDERS = {"VIDEOS": "Movies", "MUSIC": "Movies", "PICTURES": "Pictures", "DOCUMENTS": "Documents", "DOWNLOADS": "Download"}


def winapi() -> types.ModuleType:
    """Keepsake's Windows calls, as a phone does them."""
    storage = Path(STATE["storage"])
    guids = {name: name for name in FOLDERS}

    def known_folder(guid: str, fallback: str) -> Path:
        return storage / FOLDERS.get(guid, fallback)

    def recycle(path: Path) -> bool:
        return bool(PLATFORM.trash(str(path)))

    def set_clipboard_text(text: str) -> bool:
        PLATFORM.setClipboardText(text)
        return True

    nothing = lambda *_, **__: None
    return module(
        "keepsake.winapi",
        **guids,
        RUN_KEY="",
        APP_ID="Keepsake",
        DOWNLOADS_FIRST=True,
        known_folder=known_folder,
        show_in_folder=lambda path: bool(PLATFORM.showInFolder(str(path))),
        clipboard_text=lambda: str(PLATFORM.clipboardText() or ""),
        set_clipboard_text=set_clipboard_text,
        clipboard_serial=lambda: 0,
        recycle=recycle,
        in_front=lambda _: bool(PLATFORM.inFront()),
        maximized=lambda _: True,
        claim_instance=lambda: True,
        launch_command=lambda *_: "",
        flash=nothing,
        bring_forward=nothing,
        dress=nothing,
        drop_caption=nothing,
        window_command=nothing,
        wait_for_exit=nothing,
        set_app_id=nothing,
        register_identity=nothing,
        register_protocol=nothing,
        set_autostart=nothing,
        listen_for_hotkey=nothing,
    )


def tools_folder(native: Path, folder: Path) -> None:
    """Link FFmpeg where Keepsake and yt-dlp look for it, since Android only runs it from the app's library folder."""
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("ffmpeg", "ffprobe"):
        link = folder / name
        target = native / f"lib{name}.so"
        if link.is_symlink() and os.readlink(link) == str(target):
            continue
        link.unlink(missing_ok=True)
        link.symlink_to(target)


def platform(native: Path) -> None:
    """Point Keepsake's tools, folders and Windows calls at the phone's."""
    import keepsake

    keepsake.winapi = winapi()
    from keepsake import paths

    paths.PYTHON = paths.PYTHONW = "python"
    paths.AFTERIMAGE = Path("/nonexistent/afterimage")
    tools_folder(native, paths.TOOLS)

    from keepsake import commands, process

    import inproc

    inproc.install()
    real_run, real_stream = process.run, process.stream

    def run(command: list[str], timeout: float | None = None) -> subprocess.CompletedProcess[str]:
        if inproc.handles(command):
            return inproc.run(command, timeout)
        try:
            return real_run(command, timeout)
        except (FileNotFoundError, PermissionError):  # a Windows program such as shutdown.exe
            return subprocess.CompletedProcess(command, 127, "", "")

    def stream(command: list[str], cwd: Path | None = None) -> Any:
        return inproc.start(command) if inproc.handles(command) else real_stream(command, cwd)

    def kill_tree(pid: int) -> None:
        if not inproc.stop(pid):
            try:
                os.kill(pid, 9)
            except OSError:
                pass

    process.run, process.stream, process.kill_tree = run, stream, kill_tree
    process.open_with_windows = lambda target: PLATFORM.open(str(target))
    process.detach = lambda *_, **__: None
    quickjs = str(native / "libqjs.so")
    commands.runtime_args = lambda: ["--js-runtimes", f"quickjs:{quickjs}"]

    from keepsake import tools, updates

    tools.missing = lambda: []
    updates.Updater.install = install
    updates.Updater.check = lambda self, **_: None
    updates.Updater.due = lambda self: False
    looked = updates.Updater.probe

    def probe(self: Any) -> None:
        looked(self)
        # Keepsake only knows Deno and Node by name. QuickJS answers "QuickJS-ng version 0.17.0".
        line = process.first_line([quickjs, "--help"]) or ""
        self.tools["js"] = f"quickjs {line.split()[-1]}" if line else None

    updates.Updater.probe = probe
    sound_as_video()
    from keepsake import eraser

    eraser.load_models = eraser_models


class Model:
    """One of Remove Text's models in ONNX Runtime for Android, run as the eraser runs onnxruntime's.

    A phone cannot pip install onnxruntime, so Model.kt runs it, and numpy
    arrays cross as their shape and bytes.
    """

    def __init__(self, path: Path) -> None:
        self.model = jclass("com.somethingobvious.keepsake.Model")(str(path))

    def run(self, _: Any, feed: dict[str, Any], /) -> list[Any]:
        import numpy as np

        tensor = jclass("com.somethingobvious.keepsake.Model$Tensor")
        inputs = [tensor(list(value.shape), value.tobytes(), value.dtype == np.uint8) for value in feed.values()]
        try:
            outputs = self.model.run(list(feed), inputs)
        except jclass("ai.onnxruntime.OrtException") as problem:  # the eraser shows a RuntimeError's words
            raise RuntimeError(str(problem)) from problem
        return [np.frombuffer(bytes(out.data), np.uint8 if out.uint8 else np.float32).reshape(tuple(out.shape)) for out in outputs]


def eraser_models(folder: Path) -> Any:
    """Load the overlay network and MI-GAN from the models folder the desktop's setup filled."""
    from keepsake import eraser

    try:
        return eraser.Models(Model(folder / eraser.OVERLAY), Model(folder / eraser.MIGAN))
    except jclass("ai.onnxruntime.OrtException") as problem:
        raise RuntimeError(str(problem)) from problem


def updated_tools() -> Path:
    """Where downloaded yt-dlp and gallery-dl wait, ahead of the copies built into the app."""
    return Path(os.environ["APPDATA"]) / "Keepsake" / "phone-tools"


def fetch_tool(url: str, target: Path, inside: str) -> None:
    """Download a zip Python can import from, and keep it only if it holds the package."""
    import zipfile

    part = target.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=300) as reply:
        part.write_bytes(reply.read())
    with zipfile.ZipFile(part) as archive:
        if inside not in archive.namelist():
            part.unlink()
            raise ValueError(f"{url} has no {inside}")
    part.replace(target)


def install(updater: Any, channel: str, pin: str) -> None:
    """Keepsake's daily update, done without pip: yt-dlp's own zip build and gallery-dl's wheel.

    A phone app cannot pip install into itself, but Python imports straight from
    both, so the next start puts them ahead of the copies built into the app.
    """
    updater.note = f"Downloading yt-dlp {pin}" if pin else f"Downloading yt-dlp ({channel}) and gallery-dl"
    updater.remember_version()
    folder = updated_tools()
    folder.mkdir(parents=True, exist_ok=True)
    try:
        repo = "yt-dlp/yt-dlp-nightly-builds" if channel == "nightly" and not pin else "yt-dlp/yt-dlp"
        which = f"tags/{pin}" if pin else "latest"
        with urllib.request.urlopen(f"https://api.github.com/repos/{repo}/releases/{which}", timeout=60) as reply:
            release = json.load(reply)
        build = next(a["browser_download_url"] for a in release["assets"] if a["name"] == "yt-dlp")
        fetch_tool(build, folder / "yt-dlp.zip", "yt_dlp/__init__.py")
        with urllib.request.urlopen("https://pypi.org/pypi/gallery-dl/json", timeout=60) as reply:
            gallery = json.load(reply)
        wheel = next(u["url"] for u in gallery["urls"] if u["packagetype"] == "bdist_wheel")
        fetch_tool(wheel, folder / "gallery-dl.whl", "gallery_dl/__init__.py")
        got = f"Updated to yt-dlp {release['tag_name']} and gallery-dl {gallery['info']['version']}"
        updater.note = got if take_over(updater) else f"{got}. Restart Keepsake to use them."
    except (OSError, ValueError, KeyError, StopIteration) as problem:
        updater.note = f"Update failed: {problem}"
    finally:
        updater.busy = False


def take_over(updater: Any) -> bool:
    """Swap the downloaded tools in for the loaded ones, unless a run is still using them.

    Repair retries straight after updating, and it has to retry on the new yt-dlp.
    """
    import importlib
    import zipimport

    import inproc

    if inproc.RUNS:
        return False
    for name in ("yt-dlp.zip", "gallery-dl.whl"):
        path = str(updated_tools() / name)
        if path in sys.path:
            sys.path.remove(path)
        sys.path.insert(0, path)
        sys.path_importer_cache.pop(path, None)
    # zipimport keeps each zip's file table in memory, and a fresh zip at the same path needs it dropped.
    zipimport._zip_directory_cache.clear()
    importlib.invalidate_caches()
    # yt-dlp patches urllib3 and requests as it loads, and a second patch on top of
    # the first broke every request ("'Urllib3PercentREOverride' object has no
    # attribute 'sub'"), so they load fresh along with it.
    for module in list(sys.modules):
        if module.split(".")[0] in ("yt_dlp", "gallery_dl", "requests", "urllib3"):
            del sys.modules[module]
    inproc.route_ytdlp()
    import yt_dlp

    from keepsake import probe

    probe.yt_dlp = yt_dlp
    updater.probe()
    return True


def serialise(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set | frozenset | tuple):
        return list(value)
    if hasattr(value, "dump"):
        return value.dump()
    return str(value)


# Codecs an MP4 holds as they are. Anything else, which is WAV's plain PCM, becomes FLAC.
INTO_MP4 = frozenset({"aac", "mp3", "opus", "flac"})


def sound_as_video() -> None:
    """Make each sound a download leaves into a video of a still black picture.

    Android files a sound under music, which keeps it out of the gallery with the
    videos, and an MP4 with a picture track is filed as a video.
    """
    from keepsake import downloads, media
    from keepsake.jobs import run_ffmpeg
    from keepsake.links import kind

    def make_video(job: Any, name: str) -> None:
        source = Path(name)
        _, sound = media.codecs(source)
        length = media.duration(source)
        if not length:
            job.log.append(f"--- could not read {source.name}, so it stays a sound")
            return
        target = source.with_name(f"{source.stem}.video.mp4")
        quiet = ["-fflags", "+bitexact", "-flags:v", "+bitexact"] if job.options.strip_metadata else []
        # One picture a second, ending within a second before the sound does. Each picture is most
        # of the work, so this is twenty times faster than ten a second at the slower preset.
        command = [
            media.ffmpeg(), "-hide_banner", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s=640x360:r=1:d={max(1, int(length))}",
            "-i", str(source),
            "-map", "0:v", "-map", "1:a", "-map_metadata", "1",
            # The player decodes the picture too, from the last whole one before where it seeks to.
            # One every 5 seconds seeks in under 0.2 seconds on a Pixel, where 25 apart took 1.5.
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-g", "5",
            "-c:a", "copy" if sound in INTO_MP4 else "flac",
            *quiet, "-movflags", "+faststart",
            "-progress", "pipe:1", "-nostats", str(target),
        ]
        job.stage = "Making it a video"
        ok, _ = run_ffmpeg(job, command, length, target)
        if not ok:
            job.log.append(f"--- could not make {source.name} into a video")
            return
        final = source.with_suffix(".mp4")
        if final.exists():  # the same title downloaded as a video before
            final = media.beside(source, "sound", ".mp4")
        job.files.remove(str(target))
        when = source.stat()
        target.replace(final)
        os.utime(final, ns=(when.st_atime_ns, when.st_mtime_ns))
        source.unlink()
        job.files = [str(final) if n == name else n for n in job.files]

    finish = downloads.Queue.after_download

    def after_download(self: Any, job: Any) -> None:
        finish(self, job)
        tool = job.tool  # the download's own tool, not ffmpeg, is what the queue and history show
        for name in [n for n in job.files if kind(n) == "audio"]:
            if job.stop:
                break
            make_video(job, name)
        job.tool = tool
        # MediaStore read each file as it was written, before its date was set.
        for name in job.files:
            PLATFORM.scan(name)

    downloads.Queue.after_download = after_download


def start(files: str, native: str, storage: str) -> None:
    """Start Keepsake: its settings, queue and clock, with nothing drawn yet."""
    STATE["storage"] = storage
    local = Path(files) / "local"
    os.environ["APPDATA"] = str(Path(files) / "roaming")
    os.environ["LOCALAPPDATA"] = str(local)
    os.environ.setdefault("HOME", files)
    for name in ("yt-dlp.zip", "gallery-dl.whl"):
        if (updated_tools() / name).is_file():
            sys.path.insert(0, str(updated_tools() / name))
    stand_ins()
    platform(Path(native))

    from keepsake.api import Api
    from keepsake.app import App

    class PhoneApp(App):
        """Keepsake's app, saying things the phone's way."""

        def notify(self, title: str, text: str) -> None:
            PLATFORM.notify(title[:60], text[:250])

        def announce(self, job: Any) -> None:
            if not PLATFORM.inFront():
                super().announce(job)

        def sign_in(self, url: str) -> bool:
            return phone_sign_in(self, url)

    app = PhoneApp()
    app.window = Window()
    out_of_music(app)
    STATE["app"], STATE["api"] = app, Api(app)
    threading.Thread(target=app.start, daemon=True, name="keepsake").start()
    READY.set()


def out_of_music(app: Any) -> None:
    """Move folders left as the first phone versions set them, Music among them, to Download."""
    from keepsake import options

    storage = Path(STATE["storage"])
    first = {"folder": "Movies", "audio_folder": "Music", "picture_folder": "Pictures", "text_folder": "Documents"}
    if all(getattr(app.options, key) == str(storage / name / "Keepsake") for key, name in first.items()):
        app.save_settings(options.one_folder())


def phone_sign_in(app: Any, url: str) -> bool:
    """Open a site's sign-in screen and keep its session, as Windows' sign-in window does.

    Android hands back only names and values, so each cookie is written for the
    whole site and kept a year, which is what the site's own would mostly say.
    """
    import time

    from keepsake import cookies
    from keepsake.links import site_of

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url.strip("/")
    site = site_of(url)
    if "." not in site:
        return False

    def wait() -> None:
        jar: dict[str, str] = {}
        for pair in str(PLATFORM.signIn(url) or "").split(";"):
            name, equals, value = pair.strip().partition("=")
            if equals and name:
                jar[name] = value
        if jar:
            expires = int(time.time()) + 365 * 86400
            kept = [cookies.Cookie(name, value, f".{site}", "/", True, False, expires) for name, value in jar.items()]
            cookies.write_jar(cookies.jars() / f"{site}.txt", kept)
            app.notify("Signed in", f"Downloads from {site} will use this session.")

    threading.Thread(target=wait, daemon=True, name="sign-in").start()
    return True


def call(name: str, args: str) -> str:
    """Run one of the window's requests and return its answer as JSON."""
    READY.wait()
    try:
        method = getattr(STATE["api"], name)
        value = method(*json.loads(args))
        return json.dumps({"value": value}, default=serialise)
    except Exception as problem:  # the page shows a failed call, the way pywebview hands it back
        traceback.print_exc()
        return json.dumps({"error": f"{type(problem).__name__}: {problem}"})


def busy() -> str:
    """Return what the queue is doing, for the notification that keeps a download alive."""
    if not READY.is_set():
        return "{}"
    jobs = list(STATE["app"].queue.jobs.values())
    running = [job for job in jobs if job.status == "running"]
    waiting = sum(job.status == "queued" for job in jobs)
    first = running[0] if running else None
    return json.dumps({
        "running": len(running),
        "waiting": waiting,
        "title": (first.title or first.url) if first else "",
        "pct": first.pct if first and first.pct is not None else -1,
    })

