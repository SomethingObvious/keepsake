"""Looking at a link before downloading it, and searching."""

import json
import re
import subprocess
import urllib.parse
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import yt_dlp

from keepsake import cookies, failures, process
from keepsake.commands import GALLERY, YTDLP, folder_for, network_args, runtime_args
from keepsake.links import extract_urls, kind, site_of
from keepsake.options import Options

type Info = Mapping[str, object]
PREVIEW_FILES = 60  # how many files of a gallery to look at before calling it "60+"
# gallery-dl's -j dump is a list of messages, each tagged with its kind.
FOLDER_MESSAGE, FILE_MESSAGE, CHILD_MESSAGE = 2, 3, 6
SEARCHES = {
    "youtube": "ytsearch{count}:{query}",
    "youtube-date": "ytsearchdate{count}:{query}",
    "music": "https://music.youtube.com/search?q={quoted}#songs",
    "soundcloud": "scsearch{count}:{query}",
}


def text(info: Info, *names: str) -> str:
    """Return the first of several fields that holds text."""
    for name in names:
        value = info.get(name)
        if isinstance(value, str) and value:
            return value
    return ""


def whole(info: Info, name: str) -> int | None:
    """Return a field that holds a whole number."""
    value = info.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def real(info: Info, name: str) -> float | None:
    """Return a field that holds a number."""
    value = info.get(name)
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def records(info: Info, name: str) -> list[Info]:
    """Return a field that holds a list of records."""
    value = info.get(name)
    if not isinstance(value, list):
        return []
    return [cast("Info", item) for item in cast("list[object]", value) if isinstance(item, Mapping)]


def web(url: str) -> str:
    """Return a link only if it is an ordinary web address, never a script or a file."""
    return url if url.startswith(("https://", "http://")) else ""


def best_thumbnail(info: Info) -> str:
    """Return the largest thumbnail a result offers."""
    found = text(info, "thumbnail")
    if not found:
        found = next(
            (text(t, "url") for t in reversed(records(info, "thumbnails")) if text(t, "url")), ""
        )
    return web(found)


def format_rows(info: Info) -> list[dict[str, object]]:
    """Return the formats a video offers, best first, as the preview's table shows them."""
    rows: list[dict[str, object]] = []
    for entry in reversed(records(info, "formats")):
        note = text(entry, "format_note")
        if text(entry, "ext") == "mhtml" or "storyboard" in note:
            continue
        video, audio = text(entry, "vcodec") or "none", entry.get("acodec")
        identifier = text(entry, "format_id")
        height, width = whole(entry, "height"), whole(entry, "width")
        if height:
            size = f"{width or '?'}x{height}"
        else:
            size = "audio" if video == "none" else text(entry, "resolution")
        rows.append(
            {
                "id": identifier,
                "ext": text(entry, "ext"),
                "res": size,
                "fps": real(entry, "fps"),
                "vcodec": "" if video == "none" else video.split(".")[0],
                "acodec": "" if audio in (None, "none") else str(audio).split(".")[0],
                "size": real(entry, "filesize") or real(entry, "filesize_approx"),
                "tbr": real(entry, "tbr"),
                "note": note,
                "lang": text(entry, "language"),
                # A stream with no sound gets the best sound merged in.
                "spec": f"{identifier}+ba/{identifier}"
                if audio == "none" and video != "none"
                else identifier,
            }
        )
    return rows


def filename(info: Info, options: Options) -> str:
    """Return what the file will be called, using the same template yt-dlp will."""
    template = ("%(extractor_key)s/" if options.by_site else "") + options.template
    if options.mode == "audio":
        extension = options.audio_format if options.audio_format != "best" else "m4a"
    elif options.container != "original":
        extension = options.container
    else:
        extension = text(info, "ext") or "mp4"
    title = options.rename.strip() or text(info, "title")
    try:
        with yt_dlp.YoutubeDL({"outtmpl": template, "quiet": True}) as tool:
            name = str(tool.prepare_filename({**info, "ext": extension, "title": title}))
    except (yt_dlp.utils.YoutubeDLError, KeyError, TypeError, ValueError):
        return ""
    video = text(info, "id")
    if options.strip_metadata and video:
        # downloads.drop_ids takes the ID out after the download, unless it is the whole name.
        short = re.sub(rf"\s?\[{re.escape(video)}\]", "", name, count=1)
        if not Path(short).name.startswith("."):
            return short
    return name


# Lines enough to see where to cut, and quick to start.
WATCH_HEIGHT = 360


def watchable(info: Info, height: int = WATCH_HEIGHT) -> Info | None:
    """Return a small picture stream the window can play while a part is chosen."""
    streams = [
        f
        for f in records(info, "formats")
        if f.get("vcodec") not in (None, "none")
        and text(f, "protocol").startswith("http")
        and text(f, "ext") == "mp4"
        and str(f.get("vcodec", "")).startswith(("avc1", "h264"))
    ]
    streams.sort(key=tier)
    big_enough = (f for f in streams if tier(f) >= height)
    return next(big_enough, streams[-1] if streams else None)


def tier(stream: Info) -> float:
    """Return a stream's size class: the site's "360p" label, or its height when there is none.

    A wide film's 360p is only 358 pixels tall, so its height alone would pass it over for 720p.
    """
    label = re.match(r"(\d{3,4})p", text(stream, "format_note"))
    return float(label[1]) if label else real(stream, "height") or 0


def listenable(info: Info) -> str:
    """Return the smallest sound stream, to play beside a picture that has none.

    Sites rarely offer sound and picture in one plain file any more.
    """
    sounds = [
        f
        for f in records(info, "formats")
        if f.get("vcodec") == "none"
        and f.get("acodec") not in (None, "none")
        and text(f, "protocol").startswith("http")
        and text(f, "ext") in ("m4a", "webm")
    ]
    pick = min(sounds, key=lambda f: real(f, "abr") or real(f, "tbr") or 0, default=None)
    return text(pick, "url") if pick else ""


def summarise_video(info: Info, options: Options) -> dict[str, object]:
    """Return what the preview shows for a video or a playlist."""
    entries = [
        {
            "title": text(e, "title", "id"),
            "duration": real(e, "duration"),
            "url": text(e, "url", "webpage_url"),
            "thumb": best_thumbnail(e),
            "channel": text(e, "channel", "uploader"),
        }
        for e in records(info, "entries")
    ][:2000]
    chapters = [
        {"title": text(c, "title"), "start": real(c, "start_time"), "end": real(c, "end_time")}
        for c in records(info, "chapters")
    ]
    languages = sorted(
        {
            text(f, "language")
            for f in records(info, "formats")
            if text(f, "language") and f.get("vcodec") == "none"
        }
    )
    playback = options.preview_playback
    picture = watchable(info, int(playback)) if playback.isdigit() else None
    # Sound alone plays in the same player, over the thumbnail.
    watch = text(picture, "url") if picture else listenable(info) if playback == "sound" else ""
    return {
        "kind": "playlist" if info.get("_type") == "playlist" else "video",
        "title": text(info, "title", "id"),
        "uploader": text(info, "uploader", "channel"),
        "duration": real(info, "duration"),
        "site": site_of(text(info, "webpage_url")),
        "thumb": best_thumbnail(info),
        "date": text(info, "upload_date"),
        "views": whole(info, "view_count"),
        "live": text(info, "live_status"),
        "count": whole(info, "playlist_count") or len(entries),
        "entries": entries,
        "formats": format_rows(info),
        "chapters": chapters,
        "languages": languages,
        "file": filename(info, options) if info.get("_type") != "playlist" else "",
        "watch": watch,
        "listen": listenable(info) if picture and picture.get("acodec") in (None, "none") else "",
        "folder": folder_for(options),
    }


def summarise_gallery(messages: list[object], url: str) -> dict[str, object]:
    """Return what the preview shows for a gallery, from gallery-dl's -j dump."""
    files: list[tuple[str, Info]] = []
    folders: list[Info] = []
    children = 0
    for message in messages:
        if not isinstance(message, list) or not message:
            continue
        parts = [*cast("list[object]", message), None, None]
        kind_of, first, second = parts[0], parts[1], parts[2]
        if kind_of == FILE_MESSAGE and isinstance(first, str) and isinstance(second, Mapping):
            files.append((first, cast("Info", second)))
        elif kind_of == FOLDER_MESSAGE and isinstance(first, Mapping):
            folders.append(cast("Info", first))
        elif kind_of == CHILD_MESSAGE:
            children += 1
    meta: Info = folders[0] if folders else (files[0][1] if files else {})
    author = meta.get("author") or meta.get("user") or ""
    if isinstance(author, Mapping):
        author = text(cast("Info", author), "name", "nick", "username")
    album = meta.get("album")
    title = text(meta, "title", "gallery_title") or (
        text(cast("Info", album), "title") if isinstance(album, Mapping) else ""
    )
    previews = [
        web(url)
        for url, data in files
        if kind("x." + text(data, "extension")) == "image" and web(url)
    ][:24]
    return {
        "kind": "gallery",
        "title": title or str(author) or text(meta, "subcategory") or "Gallery",
        "uploader": str(author),
        "site": site_of(url),
        "count": len(files) or children,
        "more": len(files) >= PREVIEW_FILES,
        "children": children,
        "previews": previews,
    }


def complaint(stderr: str) -> str:
    """Return the line of a tool's error output that says what went wrong."""
    lines = stderr.strip().splitlines()
    return next((line for line in lines if "error" in line.lower()), lines[-1] if lines else "")


def probe(url: str, mode: str, options: Options) -> dict[str, object]:
    """Return what is behind a link, or why it could not be read."""
    found = extract_urls(url)
    if not found:
        return {"error": "That is not a link.", "advice": ""}
    url = found[0]
    credentials = cookies.arguments(cookies.chosen(options, url))
    message = ""
    if mode != "images":
        command = [
            *YTDLP,
            "-J",
            "--flat-playlist",
            "--no-warnings",
            "--color",
            "never",
            "--yes-playlist" if options.playlist else "--no-playlist",
            *network_args(options),
            *runtime_args(),
            *credentials,
            "--",
            url,
        ]
        try:
            result = process.run(command, timeout=120)
            if result.returncode == 0:
                return summarise_video(json.loads(result.stdout), options)
            message = complaint(result.stderr)
        except (subprocess.TimeoutExpired, ValueError) as problem:
            message = f"ERROR: {problem}"
        if mode != "auto":
            return {
                "error": failures.plainly(message) or "It could not be read.",
                "advice": failures.advice(message),
            }
    # Auto always asks the gallery side too, as a download does: a site that
    # turns yt-dlp away can still serve gallery-dl.
    command = [
        *GALLERY,
        "-j",
        "--range",
        f"1-{PREVIEW_FILES}",
        *network_args(options),
        *credentials,
        "--",
        url,
    ]
    try:
        result = process.run(command, timeout=180)
        dumped = json.loads(result.stdout) if result.stdout.strip().startswith("[") else None
        stderr = result.stderr
    except (subprocess.TimeoutExpired, ValueError) as problem:
        dumped, stderr = None, f"ERROR: {problem}"
    if isinstance(dumped, list) and dumped:
        return summarise_gallery(cast("list[object]", dumped), url)
    if not message or failures.unrecognised(message):
        message = complaint(stderr) or "ERROR: nothing was written"
    return {
        "error": failures.plainly(message) or "Nothing to download there.",
        "advice": failures.advice(message),
    }


def search(query: str, source: str, count: int, options: Options) -> dict[str, object]:
    """Return search results with thumbnails, from YouTube, YouTube Music or SoundCloud."""
    pattern = SEARCHES.get(source, SEARCHES["youtube"])
    target = pattern.format(
        count=count, query=query.strip(), quoted=urllib.parse.quote(query.strip())
    )
    command = [
        *YTDLP,
        "-J",
        "--flat-playlist",
        "--no-warnings",
        "--playlist-end",
        str(count),
        *network_args(options),
        *runtime_args(),
        "--",
        target,
    ]
    try:
        result = process.run(command, timeout=120)
        info = json.loads(result.stdout) if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, ValueError):
        info = None
    if not isinstance(info, Mapping):
        return {"results": [], "error": "The search did not come back. Check the connection."}
    results = [
        {
            "title": text(e, "title", "id"),
            "url": web(text(e, "url", "webpage_url")),
            "duration": real(e, "duration"),
            "channel": text(e, "channel", "uploader"),
            "views": whole(e, "view_count"),
            "thumb": best_thumbnail(e),
        }
        for e in records(cast("Info", info), "entries")
    ]
    return {"results": [r for r in results if r["url"]], "error": ""}
