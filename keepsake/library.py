"""The download folder as a library, and the archives that remember what is in it."""

import hashlib
import sqlite3
import urllib.request
import uuid
from contextlib import closing
from pathlib import Path

from keepsake import APP, paths, store
from keepsake.links import kind

MOST = 5000  # files the library shows; the newest win


def files(folder: str) -> list[dict[str, object]]:
    """Return every picture, video and sound in the folder, newest first."""
    root = Path(folder)
    found: list[dict[str, object]] = []
    if not root.is_dir():
        return found
    # A walk of the whole folder on every visit: fine to tens of thousands of
    # files; cache by directory time if it ever gets slow.
    for directory, _, names in root.walk():
        for name in names:
            what = kind(name)
            if not what:
                continue
            path = directory / name
            try:
                stat = path.stat()
            except OSError:
                continue
            found.append(
                {
                    "path": str(path),
                    "uri": path.as_uri(),
                    "name": name,
                    "kind": what,
                    "size": stat.st_size,
                    "time": getattr(stat, "st_birthtime", stat.st_mtime),
                    "folder": str(directory.relative_to(root)),
                }
            )
    found.sort(key=lambda entry: -float(str(entry["time"])))
    return found[:MOST]


def archives() -> list[dict[str, object]]:
    """Return each archive that remembers downloads, and how much it remembers."""
    candidates = [paths.DATA / "yt-dlp-archive.txt", paths.DATA / "gallery-dl-archive.sqlite3"]
    folder = paths.DATA / "archives"
    if folder.is_dir():
        candidates += sorted(folder.iterdir())
    return [
        {
            "file": path.name if path.parent == paths.DATA else f"archives/{path.name}",
            "entries": len(entries(path)),
            "tool": tool_of(path),
        }
        for path in candidates
        if path.is_file() and path.suffix in (".txt", ".sqlite3")
    ]


def tool_of(path: Path) -> str:
    """Return which tool an archive belongs to."""
    return "yt-dlp" if path.suffix == ".txt" else "gallery-dl"


def archive_path(name: str) -> Path | None:
    """Return an archive by its listed name, refusing anything outside the data folder."""
    path = (paths.DATA / name).resolve()
    inside = path.parent in (paths.DATA.resolve(), (paths.DATA / "archives").resolve())
    return path if inside and path.suffix in (".txt", ".sqlite3") and path.is_file() else None


def entries(path: Path) -> list[str]:
    """Return what an archive remembers: 'youtube abc123' and the like."""
    if path.suffix == ".txt":
        return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        # A connection's own `with` commits but leaves it open; closing() closes it.
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as db:
            return [str(row[0]) for row in db.execute("SELECT entry FROM archive")]
    except sqlite3.Error:
        return []


def forget(path: Path, lines: list[str]) -> int:
    """Make an archive forget some downloads, so they are fetched again; return how many."""
    unwanted = set(lines)
    if path.suffix == ".txt":
        kept = [line for line in entries(path) if line not in unwanted]
        removed = len(entries(path)) - len(kept)
        path.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")
        return removed
    with closing(sqlite3.connect(path)) as db, db:
        cursor = db.executemany(
            "DELETE FROM archive WHERE entry = ?", [(line,) for line in unwanted]
        )
        return cursor.rowcount


def playlists() -> list[dict[str, object]]:
    """Return the playlists, each a name and its files in order."""
    return store.load_list(paths.DATA / "playlists.json")


def save_playlist(given: object) -> list[dict[str, object]]:
    """Store one playlist, new or changed, in its place, and return them all."""
    raw = store.record(given)
    name, at = raw.get("name"), raw.get("at")
    entry: dict[str, object] = {
        "id": str(raw.get("id") or uuid.uuid4().hex[:12]),
        "name": (name.strip()[:120] if isinstance(name, str) else "") or "Playlist",
        "files": [path for path in store.items(raw.get("files")) if isinstance(path, str)],
        "at": at if isinstance(at, int) and not isinstance(at, bool) else 0,
    }
    lists = playlists()
    spot = next((i for i, p in enumerate(lists) if p.get("id") == entry["id"]), len(lists))
    lists[spot : spot + 1] = [entry]
    store.save(paths.DATA / "playlists.json", lists)
    return lists


def delete_playlist(playlist_id: str) -> list[dict[str, object]]:
    """Drop one playlist, leaving its files where they are, and return the rest."""
    lists = [p for p in playlists() if p.get("id") != playlist_id]
    store.save(paths.DATA / "playlists.json", lists)
    return lists


def cover(url: str, folder: Path) -> Path | None:
    """Return a download's own thumbnail, fetched once and kept, for a phone's player."""
    target = folder / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.img"
    if target.is_file():
        return target
    if not url.startswith("https://"):
        return None
    request = urllib.request.Request(url, headers={"User-Agent": APP})
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            data = reply.read(8_000_000)
    except (OSError, ValueError):
        return None
    folder.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target
