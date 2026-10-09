"""The running program: settings, the window, the tray, the clock and closing down."""

import os
import threading
import time
import winsound
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

import pystray
import webview
from PIL import Image

from keepsake import APP, cookies, paths, process, store, tools, winapi
from keepsake.downloads import Queue
from keepsake.jobs import Job
from keepsake.links import extract_urls, kind, site_of
from keepsake.options import BUILT_IN_PRESETS, MODES, Options, preset_values, with_preset
from keepsake.subscriptions import Subscriptions
from keepsake.updates import WEEK, Updater

if TYPE_CHECKING:
    from http.cookies import SimpleCookie

TICK = 2.0  # seconds between looks at the clock
SLOW_TICK = 60.0


class _CreateWindow(Protocol):
    def __call__(self, title: str, url: str, **options: object) -> webview.Window | None: ...


# pywebview annotates `url` with a bare Callable, which a strict type checker
# reads as partly unknown. This is the same function, described exactly.
create_window = cast("_CreateWindow", vars(webview)["create_window"])


def allow_drag(sender: object, _args: object) -> None:
    """Let `app-region: drag` in the page move the window, the way a title bar does."""
    settings = getattr(getattr(sender, "CoreWebView2", None), "Settings", None)
    if settings is not None:
        settings.IsNonClientRegionSupportEnabled = True


class App:
    """Everything that is running, and the rules that connect it."""

    def __init__(self) -> None:
        """Read the settings and restore the queue; nothing is shown yet."""
        paths.DATA.mkdir(parents=True, exist_ok=True)
        self.options = Options.load(store.load(paths.DATA / "settings.json", {}))
        self.presets = self.load_presets()
        self.queue = Queue(lambda: self.options, self.finished, self.idle)
        self.updater = Updater()
        self.subs = Subscriptions()
        self.window: webview.Window | None = None
        self.icon: pystray.Icon | None = None
        self.hwnd = 0
        self.closed = self.quitting = self.restarting = self.told_tray = False
        self.clip_serial: int | None = None
        self.title = APP
        self.last_slow = 0.0

    # --- settings and presets ---

    def save_settings(self, changes: Mapping[str, object]) -> Options:
        """Apply and store some settings."""
        before = self.options
        self.options = self.options.but({k: v for k, v in changes.items() if k != "last_update"})
        store.save(paths.DATA / "settings.json", self.options.dump())
        if before.autostart != self.options.autostart:
            winapi.set_autostart(enabled=self.options.autostart)
        self.queue.pump()  # concurrency or download hours may have changed
        return self.options

    def load_presets(self) -> dict[str, dict[str, object]]:
        """Return the presets the user saved."""
        raw = store.load(paths.DATA / "presets.json", {})
        if not isinstance(raw, Mapping):
            return {}
        return {
            str(name): cast("dict[str, object]", values)
            for name, values in cast("Mapping[object, object]", raw).items()
            if isinstance(values, dict)
        }

    def all_presets(self) -> dict[str, dict[str, object]]:
        """Return the built-in presets, then the user's."""
        return {**BUILT_IN_PRESETS, **self.presets}

    def apply_preset(self, name: str) -> Options:
        """Switch to a preset's settings."""
        values = self.all_presets().get(name)
        if values is not None:
            self.save_settings(with_preset(self.options, values).dump())
        return self.options

    def save_preset(self, name: str) -> None:
        """Keep the current settings as a preset."""
        if name.strip() and name not in BUILT_IN_PRESETS:
            self.presets[name.strip()] = preset_values(self.options)
            store.save(paths.DATA / "presets.json", self.presets)

    def delete_preset(self, name: str) -> None:
        """Forget a preset the user made."""
        if self.presets.pop(name, None) is not None:
            store.save(paths.DATA / "presets.json", self.presets)

    # --- the clock ---

    def start(self) -> None:
        """Run once the window exists: look at the tools, then keep time."""
        self.queue.pump()
        try:
            winapi.register_identity(paths.LOGO)
        except OSError:
            self.updater.note = "Could not register Keepsake's name for notifications"
        self.updater.probe()
        if tools.missing():
            self.queue.add(
                tools.JOB,
                tools.JOB,
                self.options,
                job_kind="setup",
                title="Setting up FFmpeg and Deno",
            )
        if self.updater.app["installed"]:
            try:
                winapi.register_protocol()
            except OSError:
                self.updater.note = "Could not register keepsake:// links"
        threading.Thread(target=self.tick, daemon=True, name="clock").start()

    def tick(self) -> None:
        """Retries, schedules, updates and subscriptions, all on one clock."""
        while not self.closed:
            self.queue.pump()
            if self.queue.dirty:
                self.queue.save()
            if time.time() - self.last_slow >= SLOW_TICK:
                self.last_slow = time.time()
                self.slow_tick()
            time.sleep(TICK)

    def slow_tick(self) -> None:
        """Run the once-a-minute checks."""
        o = self.options
        running = any(job.status == "running" for job in self.queue.jobs.values())
        if o.auto_update and not running and time.time() - o.last_update > WEEK:
            self.options = Options.load({**self.options.dump(), "last_update": time.time()})
            store.save(paths.DATA / "settings.json", self.options.dump())
            self.updater.update_tools(o.ytdlp_channel)
        if o.self_update and self.updater.due():
            threading.Thread(target=self.updater.check, kwargs={"apply": True}, daemon=True).start()
        for sub in self.subs.due():
            self.check_subscription(sub.id)

    # --- subscriptions ---

    def check_subscription(self, sub_id: str) -> None:
        """Queue a check of one subscription, unless one is already waiting or running."""
        sub = self.subs.get(sub_id)
        busy = any(
            job.sub == sub_id and job.status in ("queued", "running")
            for job in self.queue.jobs.values()
        )
        if not sub or busy:
            return
        sub.checked = time.time()  # not due again while this check runs
        self.subs.save()
        self.queue.add(
            sub.url,
            sub.mode,
            sub.options(self.options),
            sub=sub.id,
            title=sub.name,
            archive=str(sub.archive()),
            ytdlp_extra=sub.ytdlp_extra(),
            gallery_extra=sub.gallery_extra(),
        )

    # --- when jobs finish ---

    def finished(self, job: Job) -> None:
        """Tell the user, do what they asked for afterwards, and keep subscription counts."""
        if job.mode == tools.JOB:
            threading.Thread(target=self.updater.probe, daemon=True, name="probe").start()
            return
        if job.sub:
            new = len(job.files) if job.status == "done" else 0
            self.subs.checked(job.sub, new=new, error=job.said if job.status == "failed" else "")
            if job.status == "done" and not new:
                return  # a check that found nothing is not news
        if job.status not in ("done", "failed"):
            return
        self.announce(job)
        if job.status == "done" and job.files:
            self.after(job)

    def announce(self, job: Job) -> None:
        """Say a job ended: a notification, a flash of the taskbar, a sound."""
        o = self.options
        if o.sound:
            winsound.MessageBeep(winsound.MB_OK if job.status == "done" else winsound.MB_ICONHAND)
        looking = bool(self.hwnd) and winapi.in_front(self.hwnd)
        if looking or not o.notify:
            return
        if self.hwnd:
            winapi.flash(self.hwnd)
        if job.status == "failed":
            self.notify("Download failed", job.title)
        elif job.sub:
            self.notify(f"{len(job.files)} new from {job.title}", "Subscription")
        else:
            count = len(job.files)
            self.notify("Downloaded", job.title if count == 1 else f"{job.title} ({count} files)")

    def after(self, job: Job) -> None:
        """Open, show or copy the file, if the user asked for that."""
        first = next((name for name in job.files if kind(name)), job.files[0])
        match self.options.after:
            case "open":
                process.open_with_windows(first)
            case "reveal":
                winapi.show_in_folder(Path(first))
            case "copy":
                winapi.set_clipboard_text(first)
            case _:
                return

    def idle(self) -> None:
        """Do what was asked for when everything has finished."""
        action, self.queue.after_all = self.queue.after_all, "nothing"
        match action:
            case "notify":
                self.notify("All done", "Every download has finished.")
            case "sleep":
                process.run([paths.tool("rundll32"), "powrprof.dll,SetSuspendState", "0,1,0"])
            case "shutdown":
                # A minute's warning: `shutdown /a` in the window or a terminal cancels it.
                process.run(
                    [
                        paths.tool("shutdown"),
                        "/s",
                        "/t",
                        "60",
                        "/c",
                        "Keepsake finished its downloads.",
                    ]
                )
            case "quit":
                self.quit()
            case _:
                return

    def notify(self, title: str, text: str) -> None:
        """Show a Windows notification from the tray icon."""
        if self.icon is not None:
            try:
                self.icon.notify(text[:250], title[:60])
            except (OSError, RuntimeError):
                return

    # --- the window and the tray ---

    def before_show(self) -> None:
        """Swap Windows' title bar for the page's own, on the window's thread, before it shows."""
        native = getattr(self.window, "native", None)
        handle = getattr(native, "Handle", None)
        to_int = getattr(handle, "ToInt64", None)
        handle_number = to_int() if callable(to_int) else 0
        self.hwnd = handle_number if isinstance(handle_number, int) else 0
        if self.hwnd:
            winapi.drop_caption(self.hwnd)
        view = getattr(getattr(native, "browser", None), "webview", None)
        ready = getattr(view, "CoreWebView2InitializationCompleted", None)
        if ready is not None:
            ready += allow_drag

    def shown(self) -> None:
        """Dress the window once Windows has made it."""
        if self.hwnd:
            store.save(paths.DATA / "instance.json", {"hwnd": self.hwnd, "pid": os.getpid()})
            winapi.dress(self.hwnd, paths.ICON)

    def show(self) -> None:
        """Bring the window back, from the tray or from a second launch."""
        if self.window is None:
            return
        self.window.show()
        self.window.restore()
        if self.hwnd:
            winapi.bring_forward(self.hwnd)

    def set_title(self, title: str) -> None:
        """Show progress in the title bar and on the tray icon."""
        if title == self.title or self.window is None:
            return
        self.title = title
        self.window.set_title(title)
        if self.icon is not None:
            self.icon.title = title

    def tray(self) -> None:
        """Run the tray icon and its menu."""
        item, separator = pystray.MenuItem, pystray.Menu.SEPARATOR
        menu = pystray.Menu(
            item("Open Keepsake", self.show, default=True),
            item("Download the copied link", self.add_copied),
            separator,
            item("Pause the queue", lambda: self.queue.hold(held=True)),
            item("Resume the queue", lambda: self.queue.hold(held=False)),
            item("Check subscriptions now", self.check_all),
            item("Show the latest download", self.open_folder),
            separator,
            item("Quit Keepsake", self.quit),
        )
        # Notifications take the name and logo registered for the app id, once, in their header.
        # A copy, so the file isn't held open: an update that replaces it would fail halfway.
        with Image.open(paths.ICON) as picture:
            self.icon = pystray.Icon(APP, picture.copy(), APP, menu)
        self.icon.run()

    def folders(self) -> dict[str, Path]:
        """Return the download folders by kind: videos, music, pictures and documents."""
        o = self.options
        chosen = {
            "videos": o.folder,
            "music": o.audio_folder,
            "pictures": o.picture_folder,
            "documents": o.text_folder,
        }
        return {kind: Path(folder.strip() or o.folder) for kind, folder in chosen.items()}

    def latest_file(self) -> Path | None:
        """Return the newest downloaded file still on disk."""
        for entry in self.queue.history.entries[:200]:
            names = entry.get("files")
            for name in cast("list[object]", names) if isinstance(names, list) else []:
                if Path(str(name)).is_file():
                    return Path(str(name))
        return None

    def open_folder(self) -> None:
        """Show the latest download in its folder, or open the videos folder before the first."""
        latest = self.latest_file()
        if latest and winapi.show_in_folder(latest):
            return
        folder = self.folders()["videos"]
        folder.mkdir(parents=True, exist_ok=True)
        process.open_with_windows(folder)

    def check_all(self) -> None:
        """Check every enabled subscription now."""
        for sub in self.subs.items:
            if sub.enabled:
                self.check_subscription(sub.id)

    def add_copied(self) -> None:
        """Download whatever link is on the clipboard: the tray item and Ctrl+Alt+D."""
        found = extract_urls(winapi.clipboard_text())
        if not found:
            self.notify("Nothing to download", "The clipboard has no link in it.")
            return
        for url in found:
            self.queue.add(url, self.options.mode, self.options)
        self.notify("Added to the queue", found[0] if len(found) == 1 else f"{len(found)} links")

    def inbox(self) -> None:
        """Take links from a second copy: a keepsake:// click, or a file dropped on the icon."""
        folder = paths.DATA / "inbox"
        folder.mkdir(parents=True, exist_ok=True)
        while not self.closed:
            for message in sorted(folder.glob("*.json")):
                raw = store.load(message, {})
                message.unlink(missing_ok=True)
                self.take(raw)
            time.sleep(0.4)

    def take(self, raw: object) -> None:
        """Act on one message from another copy."""
        if not isinstance(raw, Mapping):
            return
        message = cast("Mapping[str, object]", raw)
        added: list[str] = []
        for pair in store.items(message.get("links")):
            parts = store.items(pair)
            url = parts[0] if parts else None
            mode = parts[1] if len(parts) > 1 else None
            if isinstance(url, str):
                chosen = mode if isinstance(mode, str) and mode in MODES else self.options.mode
                self.queue.add(url, chosen, self.options)
                added.append(url)
        if added:
            self.notify(
                "Added to the queue", added[0] if len(added) == 1 else f"{len(added)} links"
            )
        if message.get("show", True):
            self.show()

    # --- signing in from Keepsake's own window ---

    def sign_in(self, url: str) -> bool:
        """Open a site in a window of its own and keep its session for downloads from that site.

        The cookies are read while the window is open (pywebview can only read
        them from a window that exists) and written when it closes.
        """
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url.strip("/")
        site = site_of(url)
        if "." not in site:
            return False
        seen: dict[tuple[str, str, str], cookies.Cookie] = {}
        window = create_window(
            f"Sign in to {site} · {APP}", url, width=560, height=820, background_color="#191919"
        )
        if window is None:
            return False

        def watch() -> None:
            while window in webview.windows:
                try:
                    jars = cast("list[SimpleCookie]", window.get_cookies())
                except (OSError, RuntimeError, AttributeError):
                    jars = []
                for cookie in cookies.from_browser_window(jars):
                    seen[cookie.domain, cookie.path, cookie.name] = cookie
                time.sleep(1.5)

        def closed() -> None:
            if seen:
                cookies.write_jar(cookies.jars() / f"{site}.txt", seen.values())
                self.notify("Signed in", f"Downloads from {site} will use this session.")

        window.events.closed += closed
        threading.Thread(target=watch, daemon=True, name="sign-in").start()
        return True

    # --- closing ---

    def closing(self) -> bool | None:
        """Hide to the tray, or save the queue and let the window close."""
        if self.options.close_to_tray and self.icon and not (self.quitting or self.restarting):
            window = self.window
            if window is not None:
                threading.Thread(target=window.hide, daemon=True).start()
            if not self.told_tray:
                self.told_tray = True
                self.notify(
                    "Keepsake is still running", "Downloads and subscriptions carry on here."
                )
            return False  # cancels the close
        if not self.closed:
            self.closed = True
            self.queue.save()  # before stopping anything: running jobs come back running
            self.queue.stop_all()
        return None

    def quit(self) -> None:
        """Close for good, from the tray or after an update."""
        self.quitting = True
        self.closing()
        if self.icon is not None:
            self.icon.stop()
        if self.window is not None:
            self.window.destroy()

    def restart(self) -> None:
        """Close and open again, which is how an update takes effect."""
        self.restarting = True
        self.closing()
        # --after: the new copy waits for this one to let go of the single-instance claim.
        process.detach(
            [paths.PYTHONW, str(paths.LAUNCHER), "--after", str(os.getpid())], cwd=str(paths.ROOT)
        )
        self.quit()


def known(app: App, path: str) -> Path | None:
    """Return the path if the window may act on it: in the download folders, or downloaded here."""
    try:
        target = Path(path).resolve()
    except (OSError, ValueError):
        return None
    roots = [folder.resolve() for folder in app.folders().values()]
    if any(target.is_relative_to(root) for root in roots):
        return target
    recorded = {name for job in app.queue.jobs.values() for name in job.files}
    for entry in app.queue.history.entries[:500]:
        files = entry.get("files")
        if isinstance(files, list):
            recorded.update(str(name) for name in cast("list[object]", files))
    return target if str(target) in {str(Path(name).resolve()) for name in recorded} else None
