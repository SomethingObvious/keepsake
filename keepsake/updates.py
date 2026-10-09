"""Keeping the tools current, and Keepsake itself.

The tools update weekly by themselves, on the stable or the nightly channel,
and can be rolled back to any version they have been. Keepsake follows main:
pre-push lets through only one squashed commit at a time, with a raised
version and the whole lint and test suite passing, so each commit there is a
release.
"""

import json
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from keepsake import APP, __version__, media, paths, process, store
from keepsake.commands import GALLERY, YTDLP

PACKAGE = "yt-dlp[default,curl-cffi]"
UPSTREAM = "origin/main"
SIX_HOURS = 6 * 3600
WEEK = 7 * 86400


def version_tuple(text: str) -> tuple[int, int, int] | None:
    """Read a version such as 1.2.3."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", text.strip())
    return (int(match[1]), int(match[2]), int(match[3])) if match else None


def version_in(source: str) -> str | None:
    """Return the version that keepsake/__init__.py declares."""
    found = re.search(r'^__version__ = "([^"]+)"$', source, re.MULTILINE)
    return found[1] if found else None


class Updater:
    """Knows what is installed, and moves it forward (or back)."""

    def __init__(self) -> None:
        """Start knowing nothing; `probe` fills it in."""
        self.tools: dict[str, object] = {}
        self.busy = False
        self.note = ""
        self.lock = threading.Lock()
        self.app: dict[str, object] = {
            "version": __version__,
            "state": "idle",
            "latest": None,
            "notes": [],
            "checked": 0.0,
            "error": "",
            "installed": self.installed(),
        }

    # --- the tools ---

    def probe(self) -> None:
        """Find out what is installed."""
        ffmpeg = process.first_line([paths.tool("ffmpeg"), "-version"])
        node = process.first_line([paths.tool("node"), "--version"])
        deno = process.first_line([paths.tool("deno"), "--version"])
        runtime = (
            f"deno {deno.split()[1]}" if deno else f"node {node.lstrip('v')}" if node else None
        )
        self.tools = {
            "yt-dlp": process.first_line([*YTDLP, "--version"]),
            "gallery-dl": process.first_line([*GALLERY, "--version"]),
            "ffmpeg": ffmpeg_version(ffmpeg),
            "js": runtime,
            "encoder": media.h264_encoder(),
            "afterimage": paths.AFTERIMAGE.is_file(),
            "seen": self.seen_versions(),
        }

    def seen_versions(self) -> list[str]:
        """Return every yt-dlp version this machine has had, for rolling back."""
        return [str(v) for v in store.items(store.load(paths.DATA / "yt-dlp-versions.json", []))]

    def remember_version(self) -> None:
        """Add the installed yt-dlp version to the list of ones to roll back to."""
        current = self.tools.get("yt-dlp")
        seen = self.seen_versions()
        if isinstance(current, str) and current not in seen:
            store.save(paths.DATA / "yt-dlp-versions.json", [*seen, current][-20:])

    def update_tools(self, channel: str, pin: str = "") -> bool:
        """Start updating yt-dlp and gallery-dl in the background; False if already busy."""
        with self.lock:
            if self.busy:
                return False
            self.busy = True
        threading.Thread(target=self.install, args=(channel, pin), daemon=True).start()
        return True

    def install(self, channel: str, pin: str) -> None:
        """Install the newest (or a pinned) yt-dlp and the newest gallery-dl."""
        self.note = (
            f"Installing yt-dlp {pin}" if pin else f"Updating yt-dlp ({channel}) and gallery-dl"
        )
        before = dict(self.tools)
        self.remember_version()
        wanted = f"{PACKAGE}=={pin}" if pin else PACKAGE
        pre = ["--pre"] if channel == "nightly" and not pin else []
        command = [
            paths.PYTHON,
            "-m",
            "pip",
            "install",
            "-U",
            "--disable-pip-version-check",
            *pre,
            wanted,
            "gallery-dl",
        ]
        try:
            result = process.run(command, timeout=900)
            self.probe()
            self.remember_version()
            moved = [
                f"{name} {before.get(name) or '?'} to {self.tools.get(name)}"
                for name in ("yt-dlp", "gallery-dl")
                if before.get(name) != self.tools.get(name)
            ]
            if result.returncode != 0:
                self.note = (
                    "Update failed: " + (result.stderr.strip().splitlines() or ["pip refused"])[-1]
                )
            else:
                self.note = ("Updated " + ", ".join(moved)) if moved else "Both are already current"
        except (OSError, subprocess.TimeoutExpired) as problem:
            self.note = f"Update failed: {problem}"
        finally:
            self.busy = False

    # --- Keepsake itself ---

    def installed(self) -> bool:
        """Return whether this is the desktop copy, which updates itself.

        A git checkout follows main. A copy from the installer follows the
        releases on GitHub.
        """
        root, install = paths.ROOT.resolve(), paths.INSTALL.resolve()
        if paths.PACKAGED:
            return root.parent == install
        return root == install and (root / ".git").exists()

    def due(self) -> bool:
        """Return whether it is time to look for a new release."""
        return self.app["state"] in ("idle", "current", "failed") and (
            time.time() - float(str(self.app["checked"])) > SIX_HOURS
        )

    def check(self, *, apply: bool) -> None:
        """Move the installed copy to the newest release, if there is one."""
        app = self.app
        if not app["installed"]:
            app["state"] = "dev"
            return
        app.update(state="checking", error="")
        try:
            if paths.PACKAGED:
                self.newest_release(apply=apply)
            else:
                self.move_to_newest(apply=apply)
        except (OSError, ValueError, subprocess.TimeoutExpired, RuntimeError) as problem:
            app.update(state="failed", error=str(problem))

    def newest_release(self, *, apply: bool) -> None:
        """Look at the newest release, and fetch its app into app.next if it is newer.

        keepsake.pyw swaps app.next in on the next start, so nothing running is replaced.
        """
        app = self.app
        request = urllib.request.Request(RELEASES, headers={"User-Agent": APP})
        with urllib.request.urlopen(request, timeout=30) as reply:
            release = store.record(json.load(reply))
        app["checked"] = time.time()
        latest = str(release.get("tag_name", "")).removeprefix("v")
        app["latest"] = latest
        running, offered = version_tuple(__version__), version_tuple(latest)
        if not running or not offered or offered <= running:
            app["state"] = "current"
            return
        app["notes"] = release_notes(str(release.get("body") or ""))
        if not apply:
            app["state"] = "available"
            return
        url = asset_url(release, f"keepsake-app-{latest}.zip")
        if not url:
            message = f"Release {latest} has no app download"
            raise RuntimeError(message)
        app["state"] = "downloading"
        unpack_app(url, paths.ROOT.parent / "app.next")
        app["state"] = "ready"

    def move_to_newest(self, *, apply: bool) -> None:
        """Fetch main, and move to it if it carries a newer version than this."""
        app = self.app
        fetched = process.git("fetch", "--quiet", "origin", "main")
        app["checked"] = time.time()
        if fetched.returncode:
            lines = fetched.stderr.strip().splitlines()
            raise RuntimeError(lines[-1] if lines else "git fetch failed")
        latest = version_in(process.git("show", f"{UPSTREAM}:keepsake/__init__.py").stdout)
        app["latest"] = latest
        running, offered = version_tuple(__version__), version_tuple(latest or "")
        if not running or not offered or offered <= running:
            app["state"] = "current"
            return
        log = process.git("log", "--format=%s", f"HEAD..{UPSTREAM}").stdout.splitlines()
        app["notes"] = [line for line in log if line][:40]
        if not apply:
            app["state"] = "available"
            return
        if process.git("status", "--porcelain", "--untracked-files=no").stdout.strip():
            message = "Keepsake's folder has local changes, so it was left alone"
            raise RuntimeError(message)
        app["state"] = "downloading"
        self.checkout(UPSTREAM)
        app["state"] = "ready"

    def checkout(self, commit: str) -> None:
        """Switch the folder to a release, installing what it needs, or put it back."""
        before = process.git("rev-parse", "HEAD").stdout.strip()
        requirements = paths.ROOT / "requirements.txt"
        wanted = requirements.read_text(encoding="utf-8") if requirements.is_file() else ""
        switched = process.git("checkout", "--quiet", "--detach", commit)
        if switched.returncode:
            raise RuntimeError(switched.stderr.strip() or "git checkout failed")
        if requirements.read_text(encoding="utf-8") == wanted:
            return
        command = [
            paths.PYTHON,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            str(requirements),
        ]
        if process.run(command, timeout=900).returncode:
            process.git("checkout", "--quiet", "--detach", before)  # never code without its needs
            message = "pip could not install what the new version needs"
            raise RuntimeError(message)


RELEASES = "https://api.github.com/repos/SomethingObvious/keepsake/releases/latest"


def release_notes(body: str) -> list[str]:
    """Return a release's notes as lines, without their list marks."""
    return [line.strip().lstrip("-*").strip() for line in body.splitlines() if line.strip()][:40]


def asset_url(release: dict[str, object], name: str) -> str:
    """Return where a release's file of this name downloads from, or ""."""
    for asset in store.items(release.get("assets")):
        record = store.record(asset)
        if record.get("name") == name:
            return str(record.get("browser_download_url") or "")
    return ""


def unpack_app(url: str, target: Path) -> None:
    """Download a release's app zip and unpack it into target, replacing what was there."""
    archive = target.with_name(target.name + ".zip")
    request = urllib.request.Request(url, headers={"User-Agent": APP})
    with urllib.request.urlopen(request, timeout=120) as reply, archive.open("wb") as sink:
        shutil.copyfileobj(reply, sink)
    shutil.rmtree(target, ignore_errors=True)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(target)
    archive.unlink(missing_ok=True)
    if not (target / "keepsake" / "__init__.py").is_file():
        shutil.rmtree(target, ignore_errors=True)
        message = "The downloaded release was not a Keepsake app"
        raise RuntimeError(message)


def ffmpeg_version(line: str | None) -> str | None:
    """Return the version in ffmpeg's first line: 7.1, or the date of a nightly build.

    Nightlies say "N-125875-g5d4d3bdc61-20260731", whose N alone means nothing.
    """
    found = re.search(r"version (\S+)", line or "")
    if not found:
        return None
    version = found[1]
    dated = re.search(r"-(\d{4})(\d{2})(\d{2})$", version)
    if version.startswith("N-") and dated:
        return ".".join(dated.groups())
    return version.split("-")[0]
