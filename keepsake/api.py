"""What the window can ask for.

pywebview exposes every public method here to the page, so this is a trust
boundary: arguments arrive from JavaScript and are checked before use, file
operations only touch files Keepsake downloaded or its folders hold, and links
opened in the browser must be ordinary web addresses. Everything is held in
one private attribute, because pywebview would expose a public one too.
"""

import json
import os
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import webview

from keepsake import (
    __version__,
    cookies,
    library,
    media,
    paths,
    probe,
    process,
    store,
    textremoval,
    winapi,
)
from keepsake.app import App, known
from keepsake.links import extract_urls, kind
from keepsake.options import BUILT_IN_PRESETS, DEFAULTS, MODES, per_job
from keepsake.subscriptions import overrides_from

type Data = dict[str, object]
LINK_FILE_LIMIT = 20_000_000  # bytes: a list of links, not a video


def as_text(value: object, default: str = "") -> str:
    """Return a string from the page, or the default."""
    return value if isinstance(value, str) else default


def as_number(value: object, default: float = 0.0) -> float:
    """Return a number from the page, or the default."""
    return (
        float(value) if isinstance(value, int | float) and not isinstance(value, bool) else default
    )


def as_mapping(value: object) -> Mapping[str, object]:
    """Return a record from the page, or an empty one."""
    return cast("Mapping[str, object]", value) if isinstance(value, Mapping) else {}


def as_ids(value: object) -> list[str]:
    """Return a list of job ids from the page."""
    return (
        [v for v in cast("list[object]", value) if isinstance(v, str)]
        if isinstance(value, list)
        else []
    )


class Api:
    """The window's view of Keepsake."""

    def __init__(self, app: App) -> None:
        """Serve this running app."""
        self._app = app

    # --- starting up and keeping in step ---

    def boot(self) -> Data:
        """Return everything the window needs to draw itself the first time."""
        app = self._app
        return {
            "settings": app.options.dump(),
            "defaults": DEFAULTS,
            "browsers": cookies.browsers(),
            "afterimage": paths.AFTERIMAGE.is_file(),
            "data": str(paths.DATA),
            "version": __version__,
            "presets": list(app.all_presets()),
            "builtin": list(BUILT_IN_PRESETS),
            "accounts": cookies.sign_ins(),
        }

    def state(self) -> Data:
        """Return what changes: the jobs, the tools, updates and the queue's clock."""
        app = self._app
        return {
            "jobs": app.queue.views(),
            "tools": app.updater.tools,
            "updating": app.updater.busy,
            "note": app.updater.note,
            "app": app.updater.app,
            "reason": app.queue.reason,
            "held": app.queue.held_until,
            "after_all": app.queue.after_all,
            "subs": [sub.view() for sub in app.subs.items],
            "next": app.queue.serial + 1,
        }

    def set_title(self, title: object) -> None:
        """Show progress in the title bar."""
        self._app.set_title(as_text(title, "Keepsake")[:120])

    def window_command(self, name: object) -> None:
        """Do what a title bar button does: "minimize", "maximize" (or restore) or "close"."""
        winapi.window_command(self._app.hwnd, as_text(name))

    def maximized(self) -> bool:
        """Return whether the window fills the screen, for the button that restores it."""
        return winapi.maximized(self._app.hwnd)

    def clipboard(self) -> list[str]:
        """Return links copied since the last look, or nothing."""
        app = self._app
        serial = winapi.clipboard_serial()
        if serial == app.clip_serial:
            return []
        first, app.clip_serial = app.clip_serial is None, serial
        # Whatever was copied before launch is offered, never taken unasked.
        if first and app.options.clipboard == "auto":
            return []
        return extract_urls(winapi.clipboard_text())

    # --- settings and presets ---

    def save_settings(self, changes: object) -> Data:
        """Apply some settings and return them all."""
        return self._app.save_settings(as_mapping(changes)).dump()

    def reset_settings(self) -> Data:
        """Go back to every default, keeping the download folder."""
        app = self._app
        return app.save_settings({**DEFAULTS, "folder": app.options.folder}).dump()

    def apply_preset(self, name: object) -> Data:
        """Switch to a preset."""
        return self._app.apply_preset(as_text(name)).dump()

    def save_preset(self, name: object) -> list[str]:
        """Keep the current settings as a preset; return every preset's name."""
        self._app.save_preset(as_text(name)[:60])
        return list(self._app.all_presets())

    def delete_preset(self, name: object) -> list[str]:
        """Forget a preset; return every preset's name."""
        self._app.delete_preset(as_text(name))
        return list(self._app.all_presets())

    def export_settings(self) -> bool:
        """Save settings, presets and subscriptions to a file the user chooses."""
        target = self._dialog(webview.FileDialog.SAVE, save_filename="keepsake-settings.json")
        if not target:
            return False
        app = self._app
        bundle = {
            "settings": app.options.dump(),
            "presets": app.presets,
            "subscriptions": [sub.view() for sub in app.subs.items],
        }
        Path(target).write_text(json.dumps(bundle, indent=1), encoding="utf-8")
        return True

    def import_settings(self) -> Data | None:
        """Load settings, presets and subscriptions from a file the user chooses."""
        source = self._dialog(webview.FileDialog.OPEN, file_types=("Keepsake settings (*.json)",))
        if not source:
            return None
        bundle = as_mapping(store.load(Path(source), {}))
        app = self._app
        for name, values in as_mapping(bundle.get("presets")).items():
            if isinstance(values, dict) and name not in BUILT_IN_PRESETS:
                app.presets[name] = cast("dict[str, object]", values)
        store.save(paths.DATA / "presets.json", app.presets)
        raw_subs = bundle.get("subscriptions")
        for raw in cast("list[object]", raw_subs) if isinstance(raw_subs, list) else []:
            if isinstance(raw, Mapping):
                app.subs.add(cast("Mapping[str, object]", raw))
        return app.save_settings(as_mapping(bundle.get("settings"))).dump()

    # --- downloading ---

    def add(self, text: object, mode: object = None, extra: object = None) -> dict[str, int]:
        """Queue every link in some text: how many there were, how many were new and known."""
        app = self._app
        found = extract_urls(as_text(text))
        options = per_job(app.options, extra)
        chosen = mode if isinstance(mode, str) and mode in MODES else options.mode
        before = set(app.queue.jobs)
        for url in found:
            app.queue.add(url, chosen, options)
        known = sum(app.queue.history.downloaded_before(url) is not None for url in found)
        return {"found": len(found), "added": len(set(app.queue.jobs) - before), "before": known}

    def probe(self, url: object, mode: object = None) -> Data:
        """Return what is behind a link, and whether it was downloaded before."""
        app = self._app
        chosen = mode if isinstance(mode, str) and mode in MODES else app.options.mode
        found = probe.probe(as_text(url), chosen, app.options)
        before = app.queue.history.downloaded_before(as_text(url).strip())
        found["before"] = before.get("finished") if before else None
        return found

    def search(self, query: object, source: object, count: object = 30) -> Data:
        """Return search results."""
        amount = int(min(100, max(5, as_number(count, 30))))
        return probe.search(
            as_text(query)[:200], as_text(source, "youtube"), amount, self._app.options
        )

    def log(self, job_id: object) -> list[str]:
        """Return the end of a job's log."""
        job = self._app.queue.get(as_text(job_id))
        return list(job.log)[-800:] if job else []

    def act(self, action: object, job_ids: object) -> None:
        """Do one thing to some jobs: pause, cancel, retry, remove, or move."""
        queue, ids = self._app.queue, as_ids(job_ids)
        actions = {
            "pause": queue.pause,
            "cancel": queue.cancel,
            "retry": queue.retry,
            "remove": queue.remove,
        }
        name = as_text(action)
        if name in actions:
            queue.each(ids, actions[name])
        elif name in ("top", "up", "down", "bottom"):
            for job_id in ids:
                queue.move(job_id, name)

    def everything(self, action: object) -> None:
        """Do one thing to the whole queue."""
        queue = self._app.queue
        match as_text(action):
            case "pause":
                queue.each(queue.ids("running", "queued"), queue.pause)
            case "resume":
                queue.each(queue.ids("paused"), queue.retry)
            case "cancel":
                queue.each(queue.ids("running", "queued", "paused"), queue.cancel)
            case "retry":
                queue.each(queue.ids("failed"), queue.retry)
            case "clear":
                queue.clear_finished()
            case "hold":
                queue.hold(held=True)
            case "release":
                queue.hold(held=False)
            case _:
                return

    def schedule(self, when: object) -> None:
        """Start the queue at a time of day; empty starts it now."""
        self._app.queue.schedule(as_text(when))

    def after_all(self, action: object) -> str:
        """Choose what happens when everything has finished."""
        chosen = as_text(action)
        if chosen in ("nothing", "notify", "sleep", "shutdown", "quit"):
            self._app.queue.after_all = chosen
        return self._app.queue.after_all

    def cancel_shutdown(self) -> None:
        """Call off a shutdown Keepsake started."""
        process.run([paths.tool("shutdown"), "/a"])

    def repair(self, job_id: object) -> None:
        """Try the fixes for a refused download: clear yt-dlp's cache, then the nightly yt-dlp."""
        app = self._app
        job = app.queue.get(as_text(job_id))
        if not job:
            return
        job.repairs += 1

        def work() -> None:
            if job.repairs == 1:
                app.queue.clear_cache(job)
            else:
                app.updater.install("nightly", "")
                app.save_settings({"ytdlp_channel": "nightly"})
            app.queue.retry(job.id)

        threading.Thread(target=work, daemon=True, name="repair").start()

    # --- files ---

    def library(self) -> list[Data]:
        """Return the pictures, videos and sounds in the download folders."""
        unique: dict[str, Data] = {}
        for folder in self._app.folders().values():
            for entry in library.files(str(folder)):
                unique.setdefault(os.path.normcase(str(entry["path"])), entry)
        found = sorted(unique.values(), key=lambda entry: -float(str(entry["time"])))
        numbers = self._app.queue.history.serials()
        for entry in found[: library.MOST]:
            serial = numbers.get(os.path.normcase(str(entry["path"])))
            if serial:
                entry["serial"] = serial
        return found[: library.MOST]

    def convert(self, path: object, how: object, start: object = 0, end: object = 0) -> str:
        """Queue a conversion of a file and return its job's id, or "" when it cannot be done.

        How: compatible, a sound format, trim, exact, gif or detext.
        """
        app = self._app
        source = known(app, as_text(path))
        if (
            not source
            or not source.is_file()
            or as_text(how)
            not in ("compatible", "trim", "exact", "gif", "detext", *media.SOUND_FORMATS)
        ):
            return ""
        if as_text(how) == "detext" and (
            source.suffix.lower() not in textremoval.PICTURES
            or not any(textremoval.ready(tier) for tier in textremoval.TIERS)
        ):
            return ""
        return app.queue.add(
            str(source),
            as_text(how),
            app.options,
            job_kind="convert",
            title=source.name,
            start=as_number(start),
            end=as_number(end),
        ).id

    def text_removal(self) -> Data:
        """Return which text removal tiers are set up, and whether the best one can run here."""
        return textremoval.status()

    def set_up_text_removal(self, tier: object) -> bool:
        """Queue setting a text removal tier up: its own Python, packages and models."""
        chosen = as_text(tier)
        if chosen not in textremoval.TIERS:
            return False
        self._app.queue.add(
            f"text-removal:{chosen}",
            chosen,
            self._app.options,
            job_kind="setup",
            title=f"Setting up {'best' if chosen == 'best' else 'quick'} text removal",
        )
        return True

    def remove_text(self, paths: object) -> str:
        """Queue removing the added text from several pictures, and return the job's id or "".

        They share one job, so the remover loads its models once for all of them.
        """
        app = self._app
        pictures = [
            str(found)
            for path in as_ids(paths)
            if (found := known(app, path))
            and found.is_file()
            and found.suffix.lower() in textremoval.PICTURES
        ]
        if not pictures or not any(textremoval.ready(tier) for tier in textremoval.TIERS):
            return ""
        return app.queue.add(
            pictures[0],
            "detext",
            app.options,
            job_kind="convert",
            title=f"{len(pictures)} pictures" if len(pictures) > 1 else Path(pictures[0]).name,
            pictures=pictures,
        ).id

    def forget_text_removal(self) -> Data:
        """Delete the text remover and its models, to free the space."""
        if any(
            job.job_kind == "setup" and job.status == "running"
            for job in self._app.queue.jobs.values()
        ):
            return textremoval.status()
        textremoval.forget()
        return textremoval.status()

    def open_path(self, path: object) -> None:
        """Open a downloaded file in its usual program."""
        target = known(self._app, as_text(path))
        if target and target.exists():
            process.open_with_windows(target)

    def reveal(self, path: object) -> None:
        """Show a downloaded file in Explorer."""
        target = known(self._app, as_text(path))
        if target and target.exists() and not winapi.show_in_folder(target):
            process.open_with_windows(target.parent)

    def subtitles(self, path: object) -> list[dict[str, str]]:
        """Return a video's subtitles, beside it and inside it, for the player."""
        target = known(self._app, as_text(path))
        if not target or not target.is_file() or kind(target) != "video":
            return []
        return media.subtitle_tracks(target)

    def save_frame(self, path: object, seconds: object) -> str | None:
        """Save the frame the player is showing as a picture beside the video; return its path."""
        target = known(self._app, as_text(path))
        if not target or not target.is_file() or kind(target) != "video":
            return None
        saved = media.save_frame(target, max(0.0, as_number(seconds)))
        return str(saved) if saved else None

    def waveform(self, path: object) -> str:
        """Return a picture of a downloaded file's sound, as a link the window can show, or ""."""
        target = known(self._app, as_text(path))
        if not target or not target.is_file() or kind(target) not in ("audio", "video"):
            return ""
        drawn = media.waveform(target, paths.DATA / "waves")
        return drawn.as_uri() if drawn else ""

    def thumbnail(self, path: object) -> str:
        """Return a small picture of a downloaded file for its library tile, as a link, or ""."""
        target = known(self._app, as_text(path))
        what = kind(target) if target and target.is_file() else ""
        if not target or what not in ("image", "video"):
            return ""
        made = media.thumbnail(target, paths.DATA / "thumbs", video=what == "video")
        return made.as_uri() if made else ""

    def copy_path(self, path: object) -> bool:
        """Put a downloaded file's path on the clipboard."""
        target = known(self._app, as_text(path))
        return bool(target) and winapi.set_clipboard_text(str(target))

    def delete(self, path: object) -> bool:
        """Move a downloaded file to the Recycle Bin."""
        target = known(self._app, as_text(path))
        if not (target and target.is_file() and winapi.recycle(target)):
            return False
        # A deleted download can be fetched again: the archive forgets it.
        archive = paths.DATA / "yt-dlp-archive.txt"
        lines = self._app.queue.history.keys_for(target)
        if lines and archive.is_file():
            library.forget(archive, lines)
        return True

    def afterimage(self, path: object) -> None:
        """Open a downloaded video in Afterimage."""
        target = known(self._app, as_text(path))
        if target and kind(target) == "video" and paths.AFTERIMAGE.is_file():
            process.detach([str(paths.AFTERIMAGE), str(target)], cwd=str(paths.AFTERIMAGE.parent))

    def open_folder(self, which: object = "downloads") -> None:
        """Open a folder: "downloads" is wherever the latest download went, with it selected."""
        name = as_text(which)
        if name == "downloads":
            self._app.open_folder()
            return
        folders = {
            **self._app.folders(),
            "data": paths.DATA,
            "plugins": paths.DATA / "yt-dlp-plugins",
        }
        folder = folders.get(name, folders["videos"])
        folder.mkdir(parents=True, exist_ok=True)
        process.open_with_windows(folder)

    def open_url(self, url: object) -> None:
        """Open a web page in the browser."""
        link = as_text(url)
        if link.startswith(("http://", "https://")):
            process.open_with_windows(link)

    def pick_folder(self) -> str | None:
        """Ask for a folder."""
        return self._dialog(webview.FileDialog.FOLDER, directory=self._app.options.folder)

    def pick_file(self, purpose: object) -> str | None:
        """Ask for a cookies.txt or a file of links."""
        types = {
            "cookies": ("Cookie files (*.txt)", "All files (*.*)"),
            "links": ("Text or link files (*.txt;*.url;*.csv;*.html)", "All files (*.*)"),
        }
        return self._dialog(webview.FileDialog.OPEN, file_types=types.get(as_text(purpose), ()))

    def read_links(self, path: object) -> str:
        """Return the links in a file the user picked, one per line."""
        source = Path(as_text(path))
        if not source.is_file() or source.stat().st_size > LINK_FILE_LIMIT:
            return ""
        return "\n".join(extract_urls(source.read_text(encoding="utf-8", errors="replace")))

    def _dialog(
        self,
        kind_of: webview.FileDialog,
        *,
        directory: str = "",
        save_filename: str = "",
        file_types: tuple[str, ...] = (),
    ) -> str | None:
        window = self._app.window
        if window is None:
            return None
        chosen = window.create_file_dialog(
            kind_of, directory=directory, save_filename=save_filename, file_types=file_types
        )
        return str(chosen[0]) if chosen else None

    # --- history ---

    def history(self) -> Data:
        """Return every finished download, and the totals."""
        history = self._app.queue.history
        return {"entries": history.entries, "stats": history.stats()}

    def forget(self, entry_id: object) -> None:
        """Drop one history record."""
        self._app.queue.history.forget(as_text(entry_id))

    def clear_history(self) -> None:
        """Drop every history record."""
        self._app.queue.history.clear()

    def export_history(self) -> bool:
        """Save the history as a spreadsheet the user places."""
        target = self._dialog(webview.FileDialog.SAVE, save_filename="keepsake-history.csv")
        if not target:
            return False
        self._app.queue.history.export(Path(target))
        return True

    # --- subscriptions ---

    def add_subscription(self, raw: object) -> bool:
        """Start watching something, and look at it straight away."""
        form = as_mapping(raw)
        made = self._app.subs.add({**form, "overrides": overrides_from(form.get("overrides"))})
        if made:
            self._app.check_subscription(made.id)
        return made is not None

    def update_subscription(self, sub_id: object, raw: object) -> None:
        """Change a subscription."""
        form = dict(as_mapping(raw))
        if "overrides" in form:
            form["overrides"] = overrides_from(form["overrides"])
        self._app.subs.update(as_text(sub_id), form)

    def remove_subscription(self, sub_id: object) -> None:
        """Stop watching something."""
        self._app.subs.remove(as_text(sub_id))

    def check_subscription(self, sub_id: object) -> None:
        """Look at one subscription now; "all" looks at every one."""
        if as_text(sub_id) == "all":
            self._app.check_all()
        else:
            self._app.check_subscription(as_text(sub_id))

    # --- archives ---

    def archives(self) -> list[Data]:
        """Return the archives that remember what was downloaded, named for people."""
        names = {sub.id: sub.name for sub in self._app.subs.items}
        found = library.archives()
        for entry in found:
            stem = Path(str(entry["file"])).stem
            entry["label"] = f"Subscription: {names[stem]}" if stem in names else str(entry["file"])
        return found

    def archive_entries(self, name: object) -> list[str]:
        """Return what one archive remembers."""
        path = library.archive_path(as_text(name))
        return library.entries(path) if path else []

    def archive_forget(self, name: object, lines: object) -> int:
        """Make an archive forget some downloads, so they can be fetched again."""
        path = library.archive_path(as_text(name))
        return library.forget(path, as_ids(lines)) if path else 0

    # --- signing in ---

    def sign_in(self, url: object) -> bool:
        """Open a site to sign into; its session is kept when the window closes."""
        return self._app.sign_in(as_text(url))

    def sign_ins(self) -> list[Mapping[str, object]]:
        """Return the sites signed into from Keepsake."""
        return cookies.sign_ins()

    def forget_sign_in(self, site: object) -> list[Mapping[str, object]]:
        """Forget a sign-in."""
        cookies.forget(as_text(site))
        return cookies.sign_ins()

    # --- updates ---

    def update_tools(self, pin: object = "") -> bool:
        """Update yt-dlp and gallery-dl now, or install one yt-dlp version."""
        return self._app.updater.update_tools(self._app.options.ytdlp_channel, as_text(pin))

    def check_app_update(self) -> Data:
        """Look for a new Keepsake now."""
        updater = self._app.updater
        if updater.app["state"] not in ("checking", "downloading", "ready"):
            threading.Thread(target=updater.check, kwargs={"apply": True}, daemon=True).start()
        return updater.app

    def restart(self) -> None:
        """Restart, finishing an update."""
        self._app.restart()
