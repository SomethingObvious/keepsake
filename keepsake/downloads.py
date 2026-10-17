"""The queue: what runs, in what order and when, and what is remembered afterwards."""

import csv
import itertools
import os
import re
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from keepsake import cookies, failures, media, paths, process, store, textremoval, tools
from keepsake.commands import YTDLP, effective, folder_for
from keepsake.jobs import Job, Outcome, run_ffmpeg, run_gallery, run_ytdlp, working_folder
from keepsake.links import kind
from keepsake.options import Options

RETRY_AFTER = (30, 120, 600)  # seconds before each automatic retry of a flaky failure
FINISHED = ("done", "failed", "cancelled")
GB = 1_000_000_000
HOURS, MINUTES = 24, 60


def clock(text: str) -> tuple[int, int] | None:
    """Read a time of day typed as 1:00 or 01:00."""
    hours, _, minutes = text.strip().partition(":")
    if not (hours.isdigit() and (minutes or "0").isdigit()):
        return None
    hour, minute = int(hours), int(minutes or 0)
    return (hour, minute) if hour < HOURS and minute < MINUTES else None


def within(now: datetime, start: tuple[int, int], end: tuple[int, int]) -> bool:
    """Return whether a time of day falls in a window, which may run past midnight."""
    minute, first, last = now.hour * 60 + now.minute, start[0] * 60 + start[1], end[0] * 60 + end[1]
    return first <= minute < last if first <= last else minute >= first or minute < last


def next_time(when: tuple[int, int], now: datetime) -> datetime:
    """Return the next moment the clock shows `when`."""
    target = now.replace(hour=when[0], minute=when[1], second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


@dataclass
class History:
    """Every finished download, newest first, kept across runs."""

    path: Path
    entries: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Read what was remembered last time."""
        self.entries = store.load_list(self.path)

    def remember(self, job: Job) -> None:
        """Record a finished job, replacing an earlier record of the same one."""
        size = 0
        for name in job.files[:400]:
            try:
                size += Path(name).stat().st_size
            except OSError:
                continue
        entry: dict[str, object] = {
            "id": job.id,
            "serial": job.serial,
            "url": job.url,
            "mode": job.mode,
            "title": job.title,
            "site": job.site,
            "tool": job.tool,
            "status": job.status,
            "thumb": job.thumb,
            "files": job.files[:400],
            "nfiles": len(job.files),
            "bytes": size,
            "finished": job.finished,
            "said": job.said,
            "errors": job.errors,
            "sub": job.sub,
            "keys": job.keys,
        }
        self.entries = [entry, *(e for e in self.entries if e.get("id") != job.id)][:5000]
        store.save(self.path, self.entries)

    def earlier(self, url: str, ids: list[str]) -> dict[str, object] | None:
        """Return the last download of this link, or of a video with one of these ids."""
        return self.downloaded_before(url) or next(
            (
                e
                for e in self.entries
                if e.get("status") == "done"
                and any(str(key).split(" ")[-1] in ids for key in store.items(e.get("keys")))
            ),
            None,
        )

    def thumb_for(self, path: str) -> str:
        """Return the thumbnail of the download that made a file, or ""."""
        found = next((e for e in self.entries if path in store.items(e.get("files"))), None)
        thumb = found.get("thumb") if found else None
        return thumb if isinstance(thumb, str) else ""

    def keys_for(self, path: Path) -> list[str]:
        """Return the archive lines of the download that wrote this file."""
        target = os.path.normcase(str(path))
        return [
            str(key)
            for e in self.entries
            if any(os.path.normcase(str(name)) == target for name in store.items(e.get("files")))
            for key in store.items(e.get("keys"))
        ]

    def serials(self) -> dict[str, int]:
        """Return each downloaded file's catalogue number, by its path as Windows compares them."""
        found: dict[str, int] = {}
        for entry in reversed(self.entries):  # the newest record of a file wins
            serial = entry.get("serial")
            if isinstance(serial, int) and not isinstance(serial, bool):
                for name in store.items(entry.get("files")):
                    found[os.path.normcase(str(name))] = serial
        return found

    def forget(self, entry_id: str) -> None:
        """Drop one record."""
        self.entries = [e for e in self.entries if e.get("id") != entry_id]
        store.save(self.path, self.entries)

    def clear(self) -> None:
        """Drop every record."""
        self.entries = []
        store.save(self.path, self.entries)

    def downloaded_before(self, url: str) -> dict[str, object] | None:
        """Return the last successful download of this link, if there was one."""
        return next(
            (
                e
                for e in self.entries
                if e.get("url") == url and e.get("status") == "done" and e.get("nfiles")
            ),
            None,
        )

    def stats(self) -> dict[str, object]:
        """Return totals: how many, how much, and which sites most."""
        done = [e for e in self.entries if e.get("status") == "done"]
        sites: dict[str, int] = {}
        for entry in done:
            site = str(entry.get("site") or "other")
            sites[site] = sites.get(site, 0) + 1
        size = sum(value for e in done if isinstance(value := e.get("bytes"), int))
        top = sorted(sites.items(), key=lambda pair: -pair[1])[:6]
        return {
            "done": len(done),
            "failed": sum(e.get("status") == "failed" for e in self.entries),
            "bytes": size,
            "sites": top,
        }

    def export(self, target: Path) -> None:
        """Write the history as a spreadsheet."""
        columns = ("finished", "status", "title", "url", "site", "tool", "nfiles", "bytes")
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            for entry in self.entries:
                row = [entry.get(column, "") for column in columns]
                stamp = entry.get("finished")
                if isinstance(stamp, int | float):
                    row[0] = (
                        datetime.fromtimestamp(stamp).astimezone().isoformat(timespec="seconds")
                    )
                writer.writerow(row)


class Queue:
    """Runs jobs, a few at a time, and remembers them."""

    def __init__(
        self,
        settings: Callable[[], Options],
        on_finish: Callable[[Job], None],
        on_idle: Callable[[], None],
    ) -> None:
        """Read settings through `settings`; report each finished job, and the queue emptying."""
        self.lock = threading.RLock()
        self.on_idle = on_idle
        self.jobs: dict[str, Job] = {}
        self.settings = settings
        self.on_finish = on_finish
        self.history = History(paths.DATA / "history.json")
        self.held_until = 0.0  # a scheduled start, or infinity for "paused"
        self.reason = ""  # why nothing is starting, when that is the case
        self.after_all = "nothing"  # nothing | notify | sleep | shutdown | quit
        self.dirty = False
        self.was_busy = False
        for saved in store.load_list(paths.DATA / "queue.json"):
            job = Job.restore(saved)
            if job:
                self.jobs[job.id] = job
        # Numbers carry on from the highest one seen. Before there were numbers,
        # each download already in the history counts as one.
        seen = [
            value
            for value in (
                *(job.serial for job in self.jobs.values()),
                *(e.get("serial") for e in self.history.entries),
            )
            if isinstance(value, int)
        ]
        self.serial = max([*seen, len(self.history.entries)])
        for job in self.jobs.values():
            if not job.serial:
                self.serial += 1
                job.serial = self.serial

    # --- adding and saving ---

    def add(self, url: str, mode: str, options: Options, **fields: object) -> Job:
        """Queue a download and start it when there is room; the same one twice is one."""
        options = effective(options)
        with self.lock:
            for job in self.jobs.values():
                same = job.url == url and job.mode == mode and job.options == options
                if (
                    same
                    and job.status in ("queued", "running", "paused")
                    and all(getattr(job, name) == value for name, value in fields.items())
                ):
                    return job
            self.serial += 1
            job = Job(url=url, mode=mode, options=options, serial=self.serial)
            for name, value in fields.items():
                setattr(job, name, value)
            self.jobs[job.id] = job
        self.changed()
        self.pump()
        return job

    def changed(self) -> None:
        """Note that the queue should be saved."""
        self.dirty = True

    def save(self) -> None:
        """Write what is waiting or running, so even a crash loses nothing."""
        with self.lock:
            keep = [
                job.saved()
                for job in self.jobs.values()
                if job.status in ("queued", "running", "paused")
            ]
            self.dirty = False
        store.save(paths.DATA / "queue.json", keep)

    def views(self) -> list[dict[str, object]]:
        """Return every job as the window shows it."""
        with self.lock:
            return [job.view() for job in self.jobs.values()]

    def get(self, job_id: str) -> Job | None:
        """Return a job by its id."""
        with self.lock:
            return self.jobs.get(job_id)

    # --- when things may start ---

    def setting_up(self) -> str:
        """Return why downloads wait for FFmpeg and Deno to arrive, or an empty string."""
        busy = any(
            j.mode == tools.JOB and j.status in ("queued", "running") for j in self.jobs.values()
        )
        return "Setting up FFmpeg and Deno first" if busy else ""

    def blocked(self) -> str:
        """Return why no new download may start now, or an empty string."""
        options = self.settings()
        now = datetime.now().astimezone()
        if self.held_until == float("inf"):
            return "Queue paused"
        if self.held_until > time.time():
            return "Starts at " + datetime.fromtimestamp(self.held_until).astimezone().strftime(
                "%H:%M"
            )
        start, end = clock(options.hours_from), clock(options.hours_to)
        if start and end and not within(now, start, end):
            return f"Waiting for download hours ({options.hours_from} to {options.hours_to})"
        # The folder itself, not its root: on a phone the root is the system's own small drive.
        wanted = Path(options.folder)
        folder = next((p for p in (wanted, *wanted.parents) if p.is_dir()), None)
        try:
            free = shutil.disk_usage(folder or options.folder).free
        except OSError:
            return ""
        if free < options.min_free_gb * GB:
            where = wanted.anchor if wanted.drive else wanted
            return f"Paused: under {options.min_free_gb} GB free on {where}"
        return ""

    def pump(self) -> None:
        """Start queued jobs while there is room and nothing forbids it."""
        with self.lock:
            self.reason = self.setting_up() or self.blocked()
            running = sum(job.status == "running" for job in self.jobs.values())
            limit = max(1, self.settings().concurrency)
            for job in self.jobs.values():
                if running >= limit:
                    break
                ready = job.status == "queued" and job.retry_at <= time.time()
                if ready and (not self.reason or job.job_kind != "download"):
                    job.status, job.started = "running", time.time()
                    running += 1
                    threading.Thread(target=self.run, args=(job,), daemon=True).start()
            busy = any(job.status in ("running", "queued") for job in self.jobs.values())
            idle_now = self.was_busy and not busy
            self.was_busy = busy
        if idle_now:
            self.on_idle()

    def schedule(self, when: str) -> None:
        """Hold new downloads until a time of day; empty starts them now."""
        parsed = clock(when)
        now = datetime.now().astimezone()
        self.held_until = next_time(parsed, now).timestamp() if parsed else 0.0
        self.pump()

    def hold(self, *, held: bool) -> None:
        """Pause or resume the whole queue: running downloads carry on."""
        self.held_until = float("inf") if held else 0.0
        self.pump()

    # --- running ---

    def run(self, job: Job) -> None:
        """Run one job to the end, whatever happens inside it."""
        try:
            if job.job_kind == "setup":
                ok, message = tools.fetch(job) if job.mode == tools.JOB else textremoval.set_up(job)
            elif job.job_kind == "convert":
                ok, message = self.convert(job)
            else:
                ok, message = self.download(job)
        except (OSError, ValueError, RuntimeError) as problem:
            ok, message = False, f"ERROR: {type(problem).__name__}: {problem}"
        with self.lock:
            self.settle(job, ok=ok, message=message)
        self.changed()
        if job.status in FINISHED:
            self.on_finish(job)
        self.pump()

    def settle(self, job: Job, *, ok: bool, message: str) -> None:
        """Record how a job ended, or schedule another go at it."""
        job.proc = None
        job.speed = job.eta = None
        job.finished = time.time()
        if job.stop:
            job.status = "paused" if job.stop == "pause" else "cancelled"
            job.stage = ""
        elif ok:
            job.status, job.pct = "done", 100.0
            if job.mode != "detext":  # its stage says how many pictures lost text
                job.stage = "Nothing new" if not job.files and job.job_kind == "download" else ""
            if job.skipped and not job.files and job.job_kind == "download":
                self.name_repeat(job)
            if job.errors:  # what did arrive is kept, so say why the rest did not
                last = next(
                    (
                        line
                        for line in reversed(job.log)
                        if line.startswith("ERROR:") or "][error]" in line
                    ),
                    "",
                )
                job.said = failures.plainly(last)
            image = next((name for name in job.files if kind(name) == "image"), None)
            if not job.thumb and image:
                job.thumb = Path(image).as_uri()
        elif (
            job.options.auto_retry
            and failures.transient(message)
            and job.attempts < len(RETRY_AFTER)
        ):
            job.retry_at = time.time() + RETRY_AFTER[job.attempts]
            job.attempts += 1
            job.status, job.stage = "queued", "Retrying after a pause"
            job.log.append(f"--- will retry in {RETRY_AFTER[job.attempts - 1]} seconds")
            return
        else:
            job.status, job.stage = "failed", ""
            job.error, job.said = message, failures.plainly(message)
            job.advice = failures.advice(message)
            job.repairable = job.tool == "yt-dlp" and (
                failures.bot_check(message) or failures.unrecognised(message)
            )
        if job.status in ("done", "cancelled"):
            shutil.rmtree(working_folder(job), ignore_errors=True)
        if job.status != "paused" and job.job_kind == "download" and not job.repeat:
            self.history.remember(job)

    def name_repeat(self, job: Job) -> None:
        """Say what a skip was: the download it repeats, by title, and when that was."""
        said = "\n".join(job.log)
        ids = re.findall(
            r"\[download\] ([^\s:]+): .*?has already been recorded in the archive", said
        )
        if not ids and "has already been recorded in the archive" not in said:
            return
        earlier = self.history.earlier(job.url, ids)
        job.stage = "Already downloaded"
        job.repeat = 1.0
        if earlier:
            stamp = earlier.get("finished")
            job.repeat = float(stamp) if isinstance(stamp, int | float) and stamp else 1.0
            if not job.title or job.title == job.url:
                job.title = str(earlier.get("title") or job.title)
            job.thumb = job.thumb or str(earlier.get("thumb") or "")

    def download(self, job: Job) -> Outcome:
        """Download a link, signing in and falling back as afterimage does."""
        ok, message = self.attempt(job, cookies.chosen(job.options, job.url))
        if job.mode == "transcript" and not job.stopped():
            # Captions are fetched one language at a time, and one refused
            # translation must not throw away the ones that arrived.
            self.write_transcripts(job)
            ok = ok or bool(job.files)
        # Only when nobody named a browser or a file: quietly trying the others
        # could fetch as the wrong account.
        if (
            not ok
            and not job.stop
            and job.options.cookies == "auto"
            and failures.needs_sign_in(message)
            and not failures.cookie_store_trouble(message)
        ):
            for browser in cookies.browsers():
                if job.stopped():
                    break
                job.stage = f"Trying your {browser.title()} session"
                job.log.append(f"--- retrying with cookies from {browser}")
                ok, again = self.attempt(job, ("browser", browser))
                if ok:
                    break
                if failures.cookie_store_trouble(again) or not failures.needs_sign_in(again):
                    message = again
        if ok and not job.stop:
            self.after_download(job)
        return ok, message

    def attempt(self, job: Job, credentials: cookies.Credentials | None) -> Outcome:
        """Try the link once with one set of credentials."""
        if job.mode == "images":
            return run_gallery(job, credentials)
        ok, message = run_ytdlp(job, credentials)
        if ok or job.mode != "auto" or job.stop:
            return ok, message
        # A page with both is a video page with pictures on it, so the video
        # goes first; the gallery's error only wins when yt-dlp found no video.
        job.log.append("--- trying it as a gallery")
        ok_gallery, gallery_message = run_gallery(job, credentials)
        if ok_gallery:
            return True, ""
        if failures.unrecognised(message):
            return False, gallery_message
        job.tool = "yt-dlp"  # its error is the one being shown
        return False, message

    def after_download(self, job: Job) -> None:
        """Finish what the download itself does not: files that must play, and bare files."""
        tool = job.tool  # the download's own tool, not ffmpeg, is what the queue and history show
        if job.options.always_plays:
            for name in [n for n in job.files if kind(n) == "video"]:
                if job.stop:
                    break
                self.make_playable(job, Path(name))
        if job.options.zip:
            find_zips(job)
        pictures = [Path(n) for n in job.files if Path(n).suffix.lower() in textremoval.PICTURES]
        if job.options.remove_text in textremoval.TIERS and pictures and not job.stop:
            job.stage = "Removing added text"
            _, message = textremoval.remove_text(job, pictures, job.options.remove_text)
            if message:
                job.log.append(message)
        if job.options.strip_metadata and not job.stop:
            self.remove_metadata(job)
            drop_ids(job)
        job.tool = tool

    def remove_metadata(self, job: Job) -> None:
        """Leave each file with nothing that says what it is or where it came from.

        A gallery zipped by gallery-dl keeps its pictures' metadata inside the
        zip, which would need unpacking, stripping and packing again.
        """
        for name in list(job.files):
            path = Path(name)
            if job.stop:
                return
            job.stage = "Removing metadata"
            if path.suffix.lower() in media.STRIPPERS:
                done = media.strip_file(path)
            elif kind(name) in ("video", "audio") and path.is_file():
                target = path.with_name(f"{path.stem}.bare{path.suffix}")
                command = media.scrub_command(path, target)
                length = media.duration(path)
                done, _ = run_ffmpeg(job, command, length, target)
                # ffmpeg can exit cleanly on a file it could not read, and leave an empty one.
                if done and length and abs((media.duration(target) or 0) - length) > 1:
                    done = False
                    job.files.remove(str(target))
                    target.unlink(missing_ok=True)
                if done:
                    job.files.remove(str(target))
                    when = path.stat()
                    target.replace(path)
                    os.utime(path, ns=(when.st_atime_ns, when.st_mtime_ns))
            else:
                continue  # subtitles and transcripts are only the words
            if not done:
                job.log.append(f"--- could not remove the metadata from {path.name}")

    def write_transcripts(self, job: Job) -> None:
        """Turn each subtitle file this job wrote into plain text beside it."""
        folder = Path(folder_for(job.options))
        found: dict[Path, Path] = {}
        for pattern in ("*.vtt", "*.srt"):  # an .srt, once converted, wins over its .vtt
            for path in folder.rglob(pattern):
                ours = not job.ids or any(f"[{video}]" in path.name for video in job.ids)
                if ours and path.stat().st_mtime >= job.started - 2:
                    found[path.with_suffix("")] = path
        for subtitles in found.values():
            text = subtitles.with_suffix(".txt")
            words = media.transcript(subtitles.read_text(encoding="utf-8", errors="replace"))
            text.write_text(words, encoding="utf-8")
            job.add_file(str(text))
            job.add_file(str(subtitles))

    def make_playable(self, job: Job, source: Path) -> None:
        """Re-encode a video that some players cannot open, replacing it."""
        if media.plays_everywhere(source):
            return
        job.stage = "Making it play everywhere"
        target = source.with_name(source.stem + ".playable.mp4")
        ok, _ = run_ffmpeg(
            job, media.compatible_command(source, target), media.duration(source), target
        )
        if not ok:
            return
        final = source.with_suffix(".mp4")
        job.files.remove(str(target))
        source.unlink(missing_ok=True)
        target.replace(final)
        job.files = [str(final) if name == str(source) else name for name in job.files]
        job.add_file(str(final))

    def convert(self, job: Job) -> Outcome:
        """Run a conversion of a file already on disk."""
        source = Path(job.url)
        if not source.is_file():
            return False, "ERROR: the file is not there any more"
        span = (job.start, job.end) if job.end > job.start else (0.0, media.duration(source) or 0.0)
        makers: dict[str, tuple[str, str, Callable[[Path], list[str]]]] = {
            "compatible": (
                "plays everywhere",
                ".mp4",
                lambda target: media.compatible_command(source, target),
            ),
            **{
                name: (
                    "clip" if job.end > job.start else "audio",
                    f".{name}",
                    lambda target: media.audio_command(source, target, job.start, job.end),
                )
                for name in media.SOUND_FORMATS
            },
            "trim": (
                "clip",
                source.suffix,
                lambda target: media.trim_command(source, target, *span, exact=False),
            ),
            "exact": (
                "clip",
                ".mp4",
                lambda target: media.trim_command(source, target, *span, exact=True),
            ),
            "gif": ("gif", ".gif", lambda target: media.gif_command(source, target, *span)),
        }
        if job.mode == "detext":
            pictures = [Path(name) for name in job.pictures if Path(name).is_file()] or [source]
            job.title = source.name if len(pictures) == 1 else f"{len(pictures)} pictures"
            job.stage = "Removing added text"
            return textremoval.remove_text(job, pictures, textremoval.chosen(job))
        if job.mode not in makers:
            return False, f"ERROR: unknown conversion {job.mode}"
        note, suffix, command = makers[job.mode]
        target = media.beside(source, note, suffix)
        job.title, job.stage = target.name, "Converting"
        length = (
            span[1] - span[0]
            if job.mode in ("trim", "exact", "gif", *media.SOUND_FORMATS)
            else media.duration(source)
        )
        ok, message = run_ffmpeg(job, command(target), length, target)
        if ok and job.options.strip_metadata:
            self.remove_metadata(job)
        return ok, message

    # --- what the window can ask for ---

    def cancel(self, job_id: str) -> None:
        """Stop a job for good."""
        job = self.get(job_id)
        if job and job.status in ("running", "queued", "paused"):
            job.stop = "cancel"
            if job.status != "running":
                job.status = "cancelled"
            if job.proc and job.proc.poll() is None:
                process.kill_tree(job.proc.pid)
            self.changed()

    def pause(self, job_id: str) -> None:
        """Stop a job so it can carry on later from its partial file."""
        job = self.get(job_id)
        if job and job.status in ("running", "queued"):
            job.stop = "pause"
            if job.status == "queued":
                job.status = "paused"
            if job.proc and job.proc.poll() is None:
                process.kill_tree(job.proc.pid)
            self.changed()

    def retry(self, job_id: str) -> None:
        """Start a stopped, failed or finished job again."""
        job = self.get(job_id)
        if job and job.status in ("paused", "failed", "cancelled", "done"):
            job.log.append("--- again")
            job.reset()
            job.retry_at = 0.0
            job.status = "queued"
            self.changed()
            self.pump()

    def remove(self, job_id: str) -> None:
        """Take a job off the list. The files it wrote stay where they are."""
        self.cancel(job_id)
        with self.lock:
            self.jobs.pop(job_id, None)
        self.changed()

    def move(self, job_id: str, where: str) -> None:
        """Reorder a waiting job: top, up, down or bottom."""
        with self.lock:
            order = list(self.jobs)
            if job_id not in order:
                return
            waiting = [i for i in order if self.jobs[i].status == "queued"]
            place = order.index(job_id)
            order.remove(job_id)
            if where == "top" and waiting:
                place = order.index(waiting[0]) if waiting[0] != job_id else place
            elif where == "bottom":
                place = len(order)
            elif where == "up":
                place = max(0, place - 1)
            elif where == "down":
                place = min(len(order), place + 1)
            order.insert(place, job_id)
            self.jobs = {i: self.jobs[i] for i in order}
        self.changed()

    def each(self, job_ids: list[str], action: Callable[[str], None]) -> None:
        """Apply one action to several jobs, as the window's bulk buttons do."""
        for job_id in job_ids:
            action(job_id)

    def ids(self, *statuses: str) -> list[str]:
        """Return the ids of jobs in any of these states."""
        with self.lock:
            return [i for i, job in self.jobs.items() if job.status in statuses]

    def incomplete(self) -> list[str]:
        """Return the ids of finished jobs where some of the files failed."""
        with self.lock:
            return [i for i, job in self.jobs.items() if job.status == "done" and job.errors]

    def clear_finished(self) -> None:
        """Take finished and cancelled jobs off the list."""
        with self.lock:
            for job_id in [
                i for i, job in self.jobs.items() if job.status in ("done", "cancelled")
            ]:
                del self.jobs[job_id]
        self.changed()

    def clear_cache(self, job: Job) -> None:
        """Delete yt-dlp's cache, the first thing to try when YouTube starts refusing."""
        job.log.append("--- clearing yt-dlp's cache")
        process.run([*YTDLP, "--rm-cache-dir"], timeout=60)

    def stop_all(self) -> None:
        """Stop everything running, for closing: each comes back and carries on."""
        with self.lock:
            for job in self.jobs.values():
                if job.status == "running" and job.proc and job.proc.poll() is None:
                    job.stop = "pause"
                    process.kill_tree(job.proc.pid)


def find_zips(job: Job) -> None:
    """Swap the pictures gallery-dl zipped (and deleted) for the zip it made of them."""
    gone = [name for name in job.files if not Path(name).exists()]
    for folder in dict.fromkeys(Path(name).parent for name in gone):
        job.add_file(str(folder.with_name(folder.name + ".zip")))
    job.files = [name for name in job.files if name not in gone]


def drop_ids(job: Job) -> None:
    """Take each video's ID out of its file names, where it would point back at the source.

    A clash gets a number, the same one for the video and every file beside
    it, so a player still finds its subtitles.
    """
    for video in dict.fromkeys(job.ids):
        marker = re.compile(rf"\s?\[{re.escape(video)}\]")
        named = [Path(name) for name in job.files if marker.search(Path(name).name)]
        # Not where the ID is the whole name: there would be nothing left.
        group = [path for path in named if not marker.sub("", path.name, count=1).startswith(".")]
        renamed: list[Path] = []
        for n in itertools.count(1):
            mark = "" if n == 1 else f" ({n})"
            renamed = [old.with_name(marker.sub(mark, old.name, count=1)) for old in group]
            if not any(new.exists() for new in renamed):
                break
        for old, new in zip(group, renamed, strict=True):
            old.replace(new)
            job.files = [str(new) if name == str(old) else name for name in job.files]
