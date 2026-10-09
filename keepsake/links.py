"""Finding links in whatever was pasted, dropped or handed over."""

import re
import urllib.parse
from collections.abc import Iterable
from pathlib import Path

from keepsake.options import MODES

URL = re.compile(r"""https?://[^\s<>"']+""")
SEARCH = re.compile(r"^(yt|sc)search(date|all)?\d*:.+$")
LINK_FILES = (".txt", ".url", ".csv", ".md", ".html", ".htm")

VIDEO = frozenset({".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".flv", ".ts", ".3gp", ".wmv"})
AUDIO = frozenset(
    {
        ".mp3",
        ".m4a",
        ".opus",
        ".ogg",
        ".oga",
        ".flac",
        ".wav",
        ".aac",
        ".weba",
        ".alac",
        ".wma",
    }
)
IMAGE = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".avif",
        ".bmp",
        ".jfif",
        ".tif",
        ".tiff",
        ".svg",
        ".heic",
    }
)
TEXT = frozenset({".txt", ".srt", ".vtt"})

type Link = tuple[str, str | None]


def kind(path: str | Path) -> str | None:
    """Return what sort of media a file is by its extension, or None for anything else."""
    suffix = Path(path).suffix.lower()
    for name, suffixes in (("video", VIDEO), ("audio", AUDIO), ("image", IMAGE)):
        if suffix in suffixes:
            return name
    return None


def tidy_url(url: str) -> str:
    """Remove punctuation a sentence put after a link, but keep a Wikipedia title's ')'."""
    url = url.rstrip(".,;>]")
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1].rstrip(".,;")
    return url


def extract_urls(text: str) -> list[str]:
    """Return every link in a paste, plus yt-dlp search lines like `ytsearch5:lofi`."""
    found: list[str] = []
    for raw in str(text).splitlines():
        line = raw.strip()
        if SEARCH.match(line):
            found.append(line)
        else:
            found += [tidy_url(url) for url in URL.findall(line)]
    return list(dict.fromkeys(found))


def links_from_args(argv: Iterable[str]) -> list[Link]:
    """Return links handed over on the command line.

    keepsake:// links come from the browser bookmarklet; text and .url files are
    ones dropped on the icon; anything else is read as text.
    """
    found: list[Link] = []
    for arg in argv:
        if arg.lower().startswith("keepsake:"):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(arg).query)
            modes = query.get("mode") or []
            chosen = modes[0] if modes and modes[0] in MODES else None
            found.extend((url, chosen) for url in extract_urls((query.get("url") or [""])[0]))
        elif Path(arg).suffix.lower() in LINK_FILES and Path(arg).is_file():
            text = Path(arg).read_text(encoding="utf-8", errors="replace")
            found += [(url, None) for url in extract_urls(text)]
        else:
            found += [(url, None) for url in extract_urls(arg)]
    return found


# Hosts that are the same site under another name, for sign-ins and rules.
ALIASES = {"youtu.be": "youtube.com", "twitter.com": "x.com"}
PREFIXES = ("www.", "m.", "mobile.", "music.", "old.", "new.")


# Parts of a link that name a kind of page rather than whose page it is.
GENERIC_PARTS = frozenset(
    {
        "a",
        "album",
        "albums",
        "artworks",
        "c",
        "channel",
        "creator",
        "en",
        "gallery",
        "galleries",
        "i",
        "illustrations",
        "images",
        "ja",
        "likes",
        "media",
        "p",
        "photos",
        "post",
        "posts",
        "profile",
        "r",
        "reels",
        "status",
        "tagged",
        "tweets",
        "u",
        "user",
        "users",
    }
)
UNSAFE_IN_NAMES = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def parts(url: str) -> urllib.parse.ParseResult:
    """Return a link's parts, read as https when it names no scheme.

    Nothing for what cannot be a link: a file path with a [ in it reads as a
    broken IPv6 address, and urlparse raises.
    """
    try:
        return urllib.parse.urlparse(url if "://" in url else "https://" + url)
    except ValueError:
        return urllib.parse.urlparse("")


def gallery_name(url: str) -> str:
    """Return the folder a gallery goes in: the site, then whose it is, from its link.

    From the link rather than from gallery-dl's own folders, which nest three
    deep (site, service, user); the same link always lands in the same folder,
    so gallery-dl still skips what is already there.
    """
    parsed = parts(url)
    site = site_of(url).split(".")[0] or "gallery"
    words = [
        urllib.parse.unquote(part)
        for part in parsed.path.split("/")
        if part and part.lower() not in GENERIC_PARTS
    ]
    query = urllib.parse.parse_qsl(parsed.query)
    words += [value for key, value in query if key in {"tags", "q", "query", "search"}]
    name = " ".join(UNSAFE_IN_NAMES.sub(" ", " ".join([site, *words])).split())
    return name[:80].strip(" .") or site


def site_of(url: str) -> str:
    """Return the site a link belongs to, e.g. youtube.com for a music.youtube.com link.

    "" for what is not a web address, such as a ytsearch5: line.
    """
    host = (parts(url).hostname or "").lower()
    host = ALIASES.get(host, host)
    for prefix in PREFIXES:
        if host.startswith(prefix) and host.count(".") > 1:
            host = host.removeprefix(prefix)
    host = ALIASES.get(host, host)
    return host if "." in host else ""
