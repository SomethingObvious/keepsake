r"""Setting the text eraser up: its two models, pinned and checked, under %LOCALAPPDATA%\Keepsake.

The eraser itself (`eraser.py`) runs in Keepsake's own process. All it needs
from here is two files: the overlay network, which says what is laid on top
of a picture, and MI-GAN, which paints what was under it. Setting it up is a
queue job, so it shows its progress and can be cancelled. It also deletes
what an older setup left behind: a Python environment of its own, LaMa, the
judges and their server, the OCR models and the best tier's painter.
"""

import hashlib
import shutil
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Final

from keepsake import APP, paths
from keepsake.jobs import Job, Outcome

# Raise when what setup installs changes, so an older setup is done again.
SETUP_VERSION: Final = "2"
CHUNK: Final = 1 << 20
MB: Final = 1 << 20


@dataclass(frozen=True)
class Download:
    """A file fetched from a pinned place into the models folder, and checked against its hash."""

    url: str
    to: str  # relative to the models folder
    size: int
    sha256: str


# The network is not in the installer: it comes from this repository at this tag.
NETWORK_TAG: Final = "overlay-network-1"
# MI-GAN (Picsart AI Research, MIT), as its first author publishes it pre-converted,
# which the official repository links to.
MIGAN: Final = ("andraniksargsyan/migan", "406830d0fa60666da0071c342ad2fbc8f30c5c64")
FILES: Final = (
    Download(
        f"https://raw.githubusercontent.com/SomethingObvious/keepsake/{NETWORK_TAG}/detext/overlay.onnx",
        "overlay.onnx",
        18369363,
        "d200e7dcc32e65da2ac97aef9a7f56b832fc1b037a06311971390cabcefb0900",
    ),
    Download(
        f"https://huggingface.co/{MIGAN[0]}/resolve/{MIGAN[1]}/migan_pipeline_v2.onnx",
        "migan.onnx",
        28079181,
        "6f1f3530a1a2324b19752018ce756088b07973cda8d7d890034ace5c8a48c40b",
    ),
)


def home() -> Path:
    """Return the eraser's folder; read at call time, so a test can move it."""
    return paths.TEXT_REMOVAL


def models() -> Path:
    """Return where the models are kept."""
    return home() / "models"


def marker() -> Path:
    """Return the file that says setup finished."""
    return home() / "ready"


def ready() -> bool:
    """Return whether the eraser is set up, and by this version of Keepsake's setup."""
    try:
        return marker().read_text(encoding="utf-8").strip() == SETUP_VERSION
    except OSError:
        return False


def status() -> dict[str, object]:
    """Return what the settings show: whether it is set up, and how big it is."""
    return {"ready": ready(), "size": sum(f.size for f in FILES)}


def sha256(path: Path, job: Job) -> str:
    """Return a file's SHA-256, stopping early if the job is."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK * 8):
            if job.stopped():
                return ""
            digest.update(chunk)
    return digest.hexdigest()


def good(path: Path, want: Download, job: Job) -> bool:
    """Return whether a downloaded file is the one pinned: its size, then its hash."""
    if not path.is_file() or path.stat().st_size != want.size:
        return False
    return sha256(path, job) == want.sha256


def fetch(want: Download, job: Job, done: int, total: int) -> int:
    """Download one file, resuming a partial one, and return the bytes now done overall."""
    target = models() / want.to
    if good(target, want, job):
        return done + want.size
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    have = partial.stat().st_size if partial.is_file() else 0
    if have > want.size:
        partial.unlink()
        have = 0
    request = urllib.request.Request(want.url, headers={"User-Agent": APP})
    if have:
        request.add_header("Range", f"bytes={have}-")
    with urllib.request.urlopen(request, timeout=60) as reply, partial.open("ab") as sink:
        if have and reply.status != HTTPStatus.PARTIAL_CONTENT:  # it sent the whole file again
            sink.truncate(0)
            have = 0
        while chunk := reply.read(CHUNK):
            if job.stopped():
                return done + have
            sink.write(chunk)
            have += len(chunk)
            job.pct = 100.0 * (done + have) / total
    partial.replace(target)
    if not good(target, want, job):
        target.unlink(missing_ok=True)
        message = f"{want.to} did not match its pinned hash"
        raise ValueError(message)
    job.log.append(f"--- {want.to}: {want.size / MB:.0f} MB, checked")
    return done + want.size


def sweep() -> None:
    """Delete everything in the eraser's folder but its two models, or their partial downloads."""
    wanted = {name for f in FILES for name in (f.to, f.to + ".part")}
    for folder, keep in ((home(), {"models"}), (models(), wanted)):
        if not folder.is_dir():
            continue
        for entry in folder.iterdir():
            if entry.name in keep:
                continue
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)


def set_up(job: Job) -> Outcome:
    """Clear out what an older setup left, fetch both models, then say it is ready."""
    sweep()
    total, done = sum(f.size for f in FILES), 0
    job.stage = "Downloading its models"
    for want in FILES:
        done = fetch(want, job, done, total)
        if job.stopped():
            return False, ""
    marker().write_text(SETUP_VERSION, encoding="utf-8")
    return True, ""


def forget() -> None:
    """Remove the eraser's models entirely."""
    shutil.rmtree(home(), ignore_errors=True)
