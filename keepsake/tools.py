"""FFmpeg and Deno, which yt-dlp needs beside it, fetched on first start when this machine has none.

They go in Keepsake's own tools folder, which is on the PATH of everything
Keepsake runs, and come from where their makers publish them.
"""

import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from keepsake import APP, paths
from keepsake.jobs import Job, Outcome

CHUNK = 1 << 20


@dataclass(frozen=True)
class Tool:
    """A program Keepsake fetches, and the files it takes out of the download."""

    name: str
    url: str
    files: tuple[str, ...]


# yt-dlp's own FFmpeg builds carry its fixes. Deno runs YouTube's player code for yt-dlp.
FFMPEG = Tool(
    "FFmpeg",
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    ("ffmpeg.exe", "ffprobe.exe"),
)
DENO = Tool(
    "Deno",
    "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip",
    ("deno.exe",),
)
JOB = "tools"


def missing() -> list[Tool]:
    """Return what this machine lacks: FFmpeg, or any JavaScript runtime yt-dlp can use."""
    lacking: list[Tool] = []
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        lacking.append(FFMPEG)
    if not (shutil.which("deno") or shutil.which("node")):
        lacking.append(DENO)
    return lacking


def take_out(archive: Path, names: tuple[str, ...], folder: Path) -> list[str]:
    """Copy the named files out of a zip into a folder, from wherever the zip keeps them.

    Returns the names the zip did not have.
    """
    with zipfile.ZipFile(archive) as bundle:
        inside = {Path(member).name.lower(): member for member in bundle.namelist()}
        for name in names:
            member = inside.get(name.lower())
            if member is not None:
                with bundle.open(member) as source, (folder / name).open("wb") as sink:
                    shutil.copyfileobj(source, sink)
    return [name for name in names if not (folder / name).is_file()]


def download(tool: Tool, target: Path, job: Job) -> bool:
    """Download a tool's zip, showing how far it is. False means the job was stopped."""
    request = urllib.request.Request(tool.url, headers={"User-Agent": APP})
    with urllib.request.urlopen(request, timeout=60) as reply, target.open("wb") as sink:
        total = int(reply.headers.get("Content-Length") or 0)
        done = 0
        while chunk := reply.read(CHUNK):
            if job.stopped():
                return False
            sink.write(chunk)
            done += len(chunk)
            job.pct = 100.0 * done / total if total else None
    return True


def fetch(job: Job) -> Outcome:
    """Download and unpack every tool this machine lacks into Keepsake's tools folder."""
    folder = paths.TOOLS
    folder.mkdir(parents=True, exist_ok=True)
    for tool in missing():
        job.stage, job.pct = f"Downloading {tool.name}", 0.0
        archive = folder / f"{tool.name.lower()}.zip.part"
        try:
            if not download(tool, archive, job):
                return False, ""
            job.stage, job.pct = f"Unpacking {tool.name}", None
            lost = take_out(archive, tool.files, folder)
        finally:
            archive.unlink(missing_ok=True)
        if lost:
            return False, f"ERROR: the {tool.name} download had no {', '.join(lost)}"
        job.log.append(f"--- {tool.name}: {', '.join(tool.files)} in {folder}")
    return True, ""
