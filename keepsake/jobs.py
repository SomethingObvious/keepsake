"""One download: its state, and reading its tool's output as it runs."""

import collections
import hashlib
import json
import os
import subprocess
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from keepsake import commands, paths, process, store
from keepsake.cookies import Credentials
from keepsake.links import kind, site_of
from keepsake.options import Options

type Outcome = tuple[bool, str]  # (worked, what the tool said when it did not)

# yt-dlp's exit code for stopping where it was told to: --break-on-existing,
# --max-downloads, --break-match-filters. A subscription check ends this way.
STOPPED_AS_ASKED = 101
# What yt-dlp says when it passes something over on purpose.
PASSED_OVER = (
    "has already been recorded in the archive",
    "does not pass filter",
    "did not match filter",
    "Maximum number of downloads reached",
)

PUBLIC = (
    "id",
    "serial",
    "url",
    "mode",
    "status",
    "title",
    "item",
    "thumb",
    "site",
    "tool",
    "stage",
    "pct",
    "speed",
    "eta",
    "size",
    "error",
    "advice",
    "said",
    "added",
    "finished",
    "index",
    "count",
    "errors",
    "sub",
    "repairable",
    "retry_at",
    "attempts",
    "job_kind",
    "repeat",
)


@dataclass(eq=False)
class Job:
    """A download, or a conversion of something already downloaded."""

    url: str
    mode: str
    options: Options
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    serial: int = 0  # its number in the catalogue of everything Keepsake has fetched or made
    status: str = "queued"  # queued | running | paused | done | failed | cancelled
    title: str = ""
    thumb: str = ""
    site: str = ""
    sub: str = ""  # the subscription this check belongs to
    job_kind: str = "download"  # download | convert
    added: float = field(default_factory=time.time)
    attempts: int = 0
    retry_at: float = 0.0
    repairs: int = 0
    # A subscription check keeps its own archive and asks to stop early.
    archive: str = ""
    ytdlp_extra: list[str] = field(default_factory=list)
    gallery_extra: list[str] = field(default_factory=list)
    # A conversion: which stretch of the source, in seconds.
    start: float = 0.0
    end: float = 0.0
    started: float = 0.0
    log: collections.deque[str] = field(default_factory=lambda: collections.deque(maxlen=4000))
    # Filled in as it runs.
    item: str = ""
    tool: str = ""
    stage: str = ""
    pct: float | None = None
    speed: float | None = None
    eta: float | None = None
    size: float | None = None
    index: int | None = None
    count: int | None = None
    finished: float | None = None
    error: str = ""
    advice: str = ""
    said: str = ""
    errors: int = 0
    repairable: bool = False
    skipped: bool = False  # something was passed over on purpose: known, or filtered out
    stop: str = ""  # "" | pause | cancel
    files: list[str] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)
    keys: list[str] = field(
        default_factory=list
    )  # its lines in yt-dlp's archive, as "youtube abc123"
    # Skipped as downloaded before: when that was, or 1 when Keepsake has no record of it.
    repeat: float = 0.0
    proc: subprocess.Popen[str] | None = None

    def __post_init__(self) -> None:
        """Start with the link as the title, until the site says what it is."""
        self.title = self.title or self.url
        self.site = self.site or site_of(self.url)

    def reset(self) -> None:
        """Forget a previous attempt before trying again."""
        self.item = self.tool = self.stage = self.error = self.advice = self.said = ""
        self.pct = self.speed = self.eta = self.size = self.finished = None
        self.index = self.count = None
        self.errors = 0
        self.repairable = self.skipped = False
        self.stop = ""
        self.files, self.ids, self.keys = [], [], []
        self.repeat = 0.0
        self.proc = None

    def stopped(self) -> bool:
        """Return whether the user paused or cancelled this job, which can happen at any moment."""
        return bool(self.stop)

    def add_file(self, path: str) -> None:
        """Record a file this job wrote, once."""
        if path not in self.files and Path(path).is_file():
            self.files.append(path)

    def view(self) -> dict[str, object]:
        """Return what the window shows for this job."""
        shown: dict[str, object] = {name: getattr(self, name) for name in PUBLIC}
        media = [path for path in self.files if kind(path)]
        shown["nfiles"] = len(self.files)
        shown["first"] = (media or self.files or [""])[0]
        shown["video"] = next((path for path in self.files if kind(path) == "video"), "")
        return shown

    def saved(self) -> dict[str, object]:
        """Return what survives a restart: enough to start again from where it was."""
        return {
            "id": self.id,
            "url": self.url,
            "mode": self.mode,
            "options": self.options.dump(),
            "title": self.title,
            "thumb": self.thumb,
            "site": self.site,
            "sub": self.sub,
            "status": "paused" if self.status == "paused" else "queued",
            "job_kind": self.job_kind,
            "archive": self.archive,
            "ytdlp_extra": self.ytdlp_extra,
            "gallery_extra": self.gallery_extra,
            "start": self.start,
            "end": self.end,
            "serial": self.serial,
        }

    @classmethod
    def restore(cls, saved: dict[str, object]) -> "Job | None":
        """Rebuild a job saved by `saved`, or None if the record is damaged."""
        url, mode = saved.get("url"), saved.get("mode")
        if not isinstance(url, str) or not isinstance(mode, str):
            return None
        job = cls(url=url, mode=mode, options=Options.load(saved.get("options")))
        if isinstance(saved.get("id"), str) and saved["id"]:
            job.id = str(saved["id"])  # its working folder, and the partial file in it
        for name in ("title", "thumb", "site", "sub", "job_kind", "archive"):
            value = saved.get(name)
            if isinstance(value, str) and value:
                setattr(job, name, value)
        for name in ("ytdlp_extra", "gallery_extra"):
            setattr(job, name, [str(part) for part in store.items(saved.get(name))])
        for name in ("start", "end"):
            value = saved.get(name)
            if isinstance(value, int | float):
                setattr(job, name, float(value))
        serial = saved.get("serial")
        if isinstance(serial, int) and not isinstance(serial, bool):
            job.serial = serial
        job.status = "paused" if saved.get("status") == "paused" else "queued"
        return job


def number(text: str) -> float | None:
    """Read a number yt-dlp printed, which is 'NA' when it does not know."""
    try:
        return float(text)
    except ValueError:
        return None


def execute(
    job: Job, command: list[str], on_line: Callable[[str], None], cwd: Path | None = None
) -> int:
    """Run a tool, hand each line of its output to `on_line`, and return its exit code."""
    # `python -m yt_dlp ...` is shown as `yt-dlp ...`, the way anyone would type it.
    shown = command
    if command[1:2] == ["-m"]:
        shown = [part.replace("_", "-") for part in command[2:3]] + command[3:]
    job.log.append("$ " + subprocess.list2cmdline(shown))
    if job.stop:
        return -1
    job.stage = job.stage or "Starting"
    running = process.stream(command, cwd)
    job.proc = running
    if running.stdout is not None:
        for raw in running.stdout:
            line = raw.rstrip("\r\n")
            if line.strip():
                on_line(line)
    return running.wait()


class YtDlpReader:
    """Turns yt-dlp's tagged output into a job's progress."""

    def __init__(self, job: Job) -> None:
        """Read into this job."""
        self.job = job
        self.last_error = ""

    def __call__(self, line: str) -> None:
        """Read one line."""
        tag, _, rest = line.partition(" ")
        handler = {
            "KEEPSAKE-PROG": self.progress,
            "KEEPSAKE-PP": self.stage,
            "KEEPSAKE-META": self.meta,
            "KEEPSAKE-FILE": self.wrote,
        }.get(tag)
        if handler:
            handler(rest)
            return
        self.job.log.append(line)
        if line.startswith("ERROR:"):
            self.last_error = line
            self.job.errors += 1
        elif any(sign in line for sign in PASSED_OVER):
            self.job.skipped = True

    def progress(self, rest: str) -> None:
        """Read a progress line: bytes so far, total, estimate, speed, time left."""
        done, total, estimate, speed, eta = ([*rest.split(" "), "", "", "", "", ""])[:5]
        so_far, whole = number(done), number(total) or number(estimate)
        job = self.job
        job.pct = so_far / whole * 100 if so_far is not None and whole else None
        job.size, job.speed, job.eta = whole, number(speed), number(eta)
        if not job.stage.startswith("Downloading"):
            job.stage = "Downloading"

    def stage(self, rest: str) -> None:
        """Read which post-processing step has started."""
        name, _, status = rest.partition(" ")
        if status == "started":
            self.job.stage = commands.stage_name(name)
            self.job.speed = self.job.eta = None

    def meta(self, rest: str) -> None:
        """Read what is about to be downloaded."""
        try:
            info = store.record(json.loads(rest))
        except ValueError:
            return
        job = self.job
        job.item = str(info.get("title") or "")
        job.title = str(info.get("playlist_title") or job.item or job.title)
        thumb = str(info.get("thumbnail") or "")
        if not job.thumb and thumb.startswith(("https://", "http://")):
            job.thumb = thumb
        job.site = site_of(str(info.get("webpage_url") or "")) or job.site
        index, count = info.get("playlist_index"), info.get("playlist_count")
        job.index = index if isinstance(index, int) else None
        job.count = count if isinstance(count, int) else None
        if info.get("id"):
            job.ids.append(str(info["id"]))
            if info.get("extractor_key"):
                job.keys.append(f"{str(info['extractor_key']).lower()} {info['id']}")
        job.pct, job.stage = None, "Downloading"

    def wrote(self, rest: str) -> None:
        """Read a finished file, and give it the upload date if asked to."""
        try:
            info = store.record(json.loads(rest))
        except ValueError:
            return
        if not info.get("filepath"):
            return
        path = str(info["filepath"])
        stamp = info.get("timestamp")
        if self.job.options.file_date == "upload" and isinstance(stamp, int | float):
            try:
                os.utime(path, (stamp, stamp))
            except OSError:
                self.job.log.append(f"--- could not set the date on {path}")
        self.job.add_file(path)
        for side in side_files(info, Path(path).parent):
            self.job.add_file(side)


def side_files(info: dict[str, object], folder: Path) -> list[str]:
    """Return the other files yt-dlp wrote for one video, where they are now.

    Chapters are cut straight into place; thumbnails and subtitles are reported
    where they were written, before being moved into the video's folder.
    """
    cut = [store.record(chapter).get("filepath") for chapter in store.items(info.get("chapters"))]
    moved = [store.record(thumb).get("filepath") for thumb in store.items(info.get("thumbnails"))]
    subtitles = store.record(info.get("requested_subtitles")).values()
    moved += [store.record(track).get("filepath") for track in subtitles]
    here = [str(folder / Path(name).name) for name in moved if isinstance(name, str)]
    return [name for name in cut if isinstance(name, str)] + here


class GalleryReader:
    """Turns gallery-dl's output into a job's progress: it prints each path it writes."""

    def __init__(self, job: Job, limit: int | None) -> None:
        """Read into this job; `limit` is how many files the range allows, if known."""
        self.job = job
        self.limit = limit
        self.last_error = ""

    def __call__(self, line: str) -> None:
        """Read one line."""
        path = line.removeprefix("# ")  # a file it already had is still one of this page's
        if Path(path).is_absolute() and Path(path).is_file():
            self.file(Path(path))
            return
        self.job.log.append(line)
        if "][error]" in line or line.lower().startswith("error"):
            self.last_error = line
            self.job.errors += line.startswith("[download][error]")
        elif "skipping" in line.lower() and "archive" in line.lower():
            self.job.skipped = True

    def file(self, path: Path) -> None:
        """Record a written file and update the counts."""
        job = self.job
        job.add_file(str(path))
        count = len(job.files)
        job.stage = f"{count} file{'s' if count != 1 else ''}"
        job.pct = min(100.0, count / self.limit * 100) if self.limit else None
        if not job.thumb and kind(path) == "image":
            job.thumb = path.as_uri()
        if job.title == job.url:
            job.title = path.parent.name


def working_folder(job: Job) -> Path:
    """Return where this download keeps its unfinished files.

    One per job, so two downloads of the same video never delete each other's
    thumbnail mid-embed (which happened, even as MP3 and FLAC of one link), and
    the job's id survives a restart, so a resumed download finds its partial file.
    """
    key = hashlib.sha256(job.id.encode()).hexdigest()[:16]
    return paths.DATA / "working" / key


def finish(job: Job, code: int, last_error: str, tool: str) -> Outcome:
    """Decide whether a run worked, from its exit code and what it wrote."""
    if job.stop:
        return False, ""
    stopped_as_asked = code in (0, STOPPED_AS_ASKED)
    if stopped_as_asked and not job.files and not job.skipped and job.mode != "transcript":
        return False, "ERROR: nothing was written"
    # A playlist with one private video, or a gallery the site started
    # rate-limiting halfway: what did arrive is kept, and called done.
    if stopped_as_asked or job.files:
        return True, ""
    return False, last_error or f"ERROR: {tool} stopped with exit code {code}"


def run_ytdlp(job: Job, credentials: Credentials | None) -> Outcome:
    """Download with yt-dlp."""
    job.tool, job.pct, job.errors = "yt-dlp", None, 0
    reader = YtDlpReader(job)
    options = job.options.but({"mode": job.mode})
    archive = Path(job.archive + ".txt") if job.archive else None
    command = commands.ytdlp_command(
        options,
        job.url,
        credentials,
        archive=archive,
        extra=[*job.ytdlp_extra, "-P", f"temp:{working_folder(job)}"],
    )
    code = execute(job, command, reader)
    return finish(job, code, reader.last_error, "yt-dlp")


def run_gallery(job: Job, credentials: Credentials | None) -> Outcome:
    """Download with gallery-dl."""
    job.tool, job.pct, job.errors = "gallery-dl", None, 0
    job.stage = "Collecting"
    reader = GalleryReader(job, commands.range_size(job.options.range))
    archive = Path(job.archive + ".sqlite3") if job.archive else None
    command = commands.gallery_command(
        job.options,
        job.url,
        credentials,
        archive=archive,
        extra=job.gallery_extra,
    )
    code = execute(job, command, reader)
    return finish(job, code, reader.last_error, "gallery-dl")


class FfmpegReader:
    """Turns ffmpeg's -progress output into a percentage."""

    def __init__(self, job: Job, length: float | None) -> None:
        """Read into this job; `length` is the output's expected duration in seconds."""
        self.job = job
        self.length = length
        self.last_error = ""

    def __call__(self, line: str) -> None:
        """Read one line."""
        key, _, value = line.partition("=")
        if key == "out_time_us" and self.length:
            done = number(value)
            if done is not None:
                self.job.pct = max(0.0, min(100.0, done / 1_000_000 / self.length * 100))
        elif key == "speed":
            self.job.stage = f"{self.job.stage.split(' · ')[0]} · {value.strip()}"
        elif "=" not in line:
            self.job.log.append(line)
            if "error" in line.lower():
                self.last_error = line


def run_ffmpeg(job: Job, command: list[str], length: float | None, target: Path) -> Outcome:
    """Run one ffmpeg conversion and keep its output file."""
    job.tool, job.pct = "ffmpeg", 0.0
    reader = FfmpegReader(job, length)
    code = execute(job, command, reader)
    if job.stop:
        target.unlink(missing_ok=True)
        return False, ""
    if code != 0 or not target.is_file():
        target.unlink(missing_ok=True)
        return False, reader.last_error or f"ERROR: ffmpeg stopped with exit code {code}"
    job.add_file(str(target))
    return True, ""
