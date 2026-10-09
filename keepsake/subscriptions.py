"""Watching a channel, playlist or profile, and fetching only what is new.

A check is an ordinary download with its own archive and permission to stop
early: yt-dlp stops at the first video it already has (channels list newest
first), and gallery-dl stops after a few files in a row it already has. So a
check of a channel with ten thousand videos costs a page or two, not an hour.
"""

import re
import time
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Self, cast

from keepsake import paths, store
from keepsake.options import Options

HOUR = 3600
LOOK_AT = 50  # the newest items a check looks at, so a first check is never the whole channel
SAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class Subscription:
    """One thing being watched."""

    url: str
    name: str
    mode: str = "auto"
    every: float = 6.0  # hours between checks
    start: str = "new"  # new: only what appears from now on | all: everything there is
    since: str = field(default_factory=lambda: datetime.now().astimezone().strftime("%Y%m%d"))
    enabled: bool = True
    overrides: dict[str, object] = field(default_factory=dict)  # filters and format for this one
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    checked: float = 0.0
    found: int = 0  # files fetched over its whole life
    last_new: int = 0  # files fetched by the latest check
    last_error: str = ""

    @classmethod
    def load(cls, raw: Mapping[str, object]) -> Self | None:
        """Rebuild a stored subscription, or None if it is damaged."""
        url, name = raw.get("url"), raw.get("name")
        if not isinstance(url, str) or not isinstance(name, str):
            return None
        made = cls(url=url, name=name)
        for spec in fields(cls):
            value = raw.get(spec.name)
            default = getattr(made, spec.name)
            if value is not None and isinstance(value, type(default)):
                setattr(made, spec.name, value)
            elif (
                isinstance(default, float)
                and isinstance(value, int)
                and not isinstance(value, bool)
            ):
                setattr(made, spec.name, float(value))
        return made

    def due(self, now: float) -> bool:
        """Return whether it is time to look again."""
        return self.enabled and now - self.checked >= self.every * HOUR

    def folder(self, options: Options) -> Path:
        """Return where this subscription's files go: a folder named after it."""
        return Path(options.folder) / (SAFE_NAME.sub("_", self.name).strip(" .") or "Subscription")

    def options(self, base: Options) -> Options:
        """Return the options a check runs with: current ones, its overrides, its folder."""
        values = base.but(self.overrides).dump()
        values.update(
            {
                "folder": str(self.folder(base)),
                "by_site": False,
                "playlist": True,
                "template": "%(upload_date>%Y-%m-%d|undated)s %(title).170B [%(id)s].%(ext)s",
                "archive": False,
                "ignore_archive": False,
                "items": "",
                "format": "",
            }
        )
        return Options.load(values)

    def archive(self) -> Path:
        """Return this subscription's archive, without its extension: each tool adds its own."""
        return paths.DATA / "archives" / self.id

    def ytdlp_extra(self) -> list[str]:
        """Return what makes a yt-dlp check cheap: stop at the first known video."""
        extra = [
            "--break-on-existing",
            "--break-per-input",
            "--lazy-playlist",
            "--playlist-end",
            str(LOOK_AT),
        ]
        if self.start == "new":
            # Newest first, so the first older video ends the check.
            extra += ["--break-match-filters", f"upload_date>={self.since}"]
        return extra

    def gallery_extra(self) -> list[str]:
        """Return what makes a gallery-dl check cheap: stop after three known files in a row."""
        extra = ["-A", "3"]
        if self.start == "new":
            year, month, day = (
                self.since[:4],
                self.since[4:6].lstrip("0"),
                self.since[6:].lstrip("0"),
            )
            extra += ["--filter", f"date >= datetime({year}, {month}, {day})"]
        return extra

    def view(self) -> dict[str, object]:
        """Return what the window shows."""
        return asdict(self)


class Subscriptions:
    """Every subscription, kept on disk."""

    def __init__(self) -> None:
        """Read them from the data folder."""
        self.path = paths.DATA / "subscriptions.json"
        self.items: list[Subscription] = [
            made for raw in store.load_list(self.path) if (made := Subscription.load(raw))
        ]

    def save(self) -> None:
        """Write them back."""
        store.save(self.path, [item.view() for item in self.items])

    def get(self, sub_id: str) -> Subscription | None:
        """Return one by its id."""
        return next((item for item in self.items if item.id == sub_id), None)

    def add(self, raw: Mapping[str, object]) -> Subscription | None:
        """Add a subscription from the window's form."""
        made = Subscription.load({**raw, "id": uuid.uuid4().hex[:10], "checked": 0.0})
        if not made or not made.url.startswith(("http://", "https://")):
            return None
        if not made.name.strip():
            made.name = made.url.split("//", 1)[-1].strip("/")
        self.items.append(made)
        self.save()
        return made

    def update(self, sub_id: str, raw: Mapping[str, object]) -> None:
        """Change a subscription's settings."""
        current = self.get(sub_id)
        if not current:
            return
        merged = Subscription.load({**current.view(), **raw, "id": sub_id})
        if merged:
            self.items = [merged if item.id == sub_id else item for item in self.items]
            self.save()

    def remove(self, sub_id: str) -> None:
        """Stop watching. Files already fetched stay where they are."""
        self.items = [item for item in self.items if item.id != sub_id]
        self.save()

    def due(self) -> list[Subscription]:
        """Return the subscriptions that should be checked now."""
        now = time.time()
        return [item for item in self.items if item.due(now)]

    def checked(self, sub_id: str, *, new: int, error: str) -> None:
        """Record the result of a check."""
        item = self.get(sub_id)
        if item:
            item.checked, item.last_new, item.last_error = time.time(), new, error
            item.found += new
            self.save()


def overrides_from(raw: object) -> dict[str, object]:
    """Keep only the settings a subscription may override."""
    allowed = {
        "quality",
        "container",
        "codec",
        "audio_format",
        "audio_quality",
        "skip_shorts",
        "skip_live",
        "skip_members",
        "min_duration",
        "max_duration",
        "title_match",
        "title_skip",
        "subs",
        "sponsorblock",
        "music",
        "embed_thumbnail",
        "always_plays",
    }
    if not isinstance(raw, Mapping):
        return {}
    return {k: v for k, v in cast("Mapping[str, object]", raw).items() if k in allowed}
