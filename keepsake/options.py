"""Every setting, typed, with its default, and the presets built from them.

Settings are stored as plain JSON. `Options.load` is the only way in, and it
checks every value against the default's type, so a hand-edited or damaged
settings file costs one setting its value rather than the whole program.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any, Self, cast

from keepsake import APP, store, winapi

MODES = ("auto", "video", "audio", "images", "transcript")


def own_folders() -> dict[str, str]:
    """Return the system's own folder for each kind of download, as its other programs use them."""
    return {
        "folder": str(winapi.known_folder(winapi.VIDEOS, "Videos") / APP),
        "audio_folder": str(winapi.known_folder(winapi.MUSIC, "Music") / APP),
        "picture_folder": str(winapi.known_folder(winapi.PICTURES, "Pictures") / APP),
        "text_folder": str(winapi.known_folder(winapi.DOCUMENTS, "Documents") / APP),
    }


def one_folder() -> dict[str, str]:
    """Return every kind of download going to one Keepsake folder in Downloads."""
    downloads = str(winapi.known_folder(winapi.DOWNLOADS, "Downloads") / APP)
    return dict.fromkeys(own_folders(), downloads)


FIRST_FOLDERS = one_folder() if winapi.DOWNLOADS_FIRST else own_folders()


@dataclass(frozen=True, slots=True)
class Options:
    """What a download does, how the queue behaves, and how Keepsake looks after itself."""

    # --- saving ---
    # A folder for each kind. Empty means "with the videos".
    folder: str = FIRST_FOLDERS["folder"]
    audio_folder: str = FIRST_FOLDERS["audio_folder"]
    picture_folder: str = FIRST_FOLDERS["picture_folder"]
    text_folder: str = FIRST_FOLDERS["text_folder"]
    by_site: bool = False  # off: videos loose, one folder per gallery
    template: str = "%(title).180B [%(id)s].%(ext)s"
    file_date: str = "download"  # download | upload
    restrict_names: bool = False
    rename: str = ""  # a title typed in the preview, for one download

    # --- what to fetch ---
    mode: str = "auto"  # auto | video | audio | images | transcript
    quality: str = "best"  # best | 2160 | 1440 | 1080 | 720 | 480 | 360
    container: str = "mp4"  # mp4 | mkv | webm | original
    # H.264 only breaks a tie after resolution, so this never costs pixels; it
    # is what makes "best" a file every editor and television opens.
    codec: str = "h264"  # any | h264 | h265 | vp9 | av1
    prefer_sdr: bool = True
    always_plays: bool = False  # re-encode to H.264/AAC MP4 after downloading
    audio_format: str = "mp3"  # best | mp3 | m4a | opus | flac | wav
    audio_quality: str = "0"  # 0 (best VBR) .. 10, or a bitrate like 320K
    audio_lang: str = ""  # "" original | "all" | a language code such as en
    format: str = ""  # an exact yt-dlp format picked in the preview
    playlist: bool = False
    playlist_reverse: bool = False
    items: str = ""
    section: str = ""
    chapters: str = ""  # chapter titles picked in the preview, one per line
    precise_cuts: bool = False
    subs: str = "off"  # off | download | embed
    # Exact codes: "en.*" also matches YouTube's machine translations (en-de,
    # en-fr...), dozens of tracks that get the whole request rate-limited.
    sub_langs: str = "en,en-US,en-GB"
    auto_subs: bool = False
    # Every file keeps only its picture and sound: no tags, cover art,
    # chapters, link or camera data, and nothing written beside it that
    # would say the same. It overrides the embedding switches below.
    strip_metadata: bool = True
    embed_thumbnail: bool = True
    square_cover: bool = True  # crop cover art to 1:1 for music
    embed_metadata: bool = True
    embed_chapters: bool = True
    split_chapters: bool = False
    write_thumbnail: bool = False
    write_description: bool = False
    write_info_json: bool = False
    write_comments: bool = False
    max_comments: str = "500"
    sponsorblock: str = "off"  # off | mark | remove
    sponsor_categories: str = "sponsor,selfpromo,interaction"
    music: bool = False
    live_from_start: bool = False
    wait_for_live: bool = False
    archive: bool = False
    ignore_archive: bool = False  # "download it again anyway", for one download

    # --- which videos of a playlist or channel ---
    min_duration: str = ""
    max_duration: str = ""
    date_after: str = ""
    date_before: str = ""
    skip_shorts: bool = False
    skip_live: bool = False
    skip_members: bool = False
    title_match: str = ""
    title_skip: str = ""
    max_items: str = ""

    # --- galleries ---
    range: str = ""
    gallery_filter: str = ""
    write_metadata: bool = False
    zip: bool = False
    ugoira: str = "copy"  # copy (MKV, frames untouched) | off (the zip) | webm | mp4 | gif
    # Take text added on top of pictures (captions, stickers, watermarks) off
    # them, keeping text that is part of the picture. Off until set up.
    remove_text: str = "off"  # off | quick | best

    # --- sign-in, network and politeness ---
    cookies: str = "auto"  # none | auto | <browser> | file
    cookie_file: str = ""
    proxy: str = ""
    rate: str = ""
    impersonate: str = ""  # "" | chrome | edge | safari | firefox
    politeness: str = "normal"  # off | normal | careful
    fragments: int = 4
    retries: int = 10
    concurrency: int = 3
    auto_retry: bool = True
    trim_names: int = 150

    # --- the queue's clock ---
    hours_from: str = ""  # only download between these, e.g. 01:00 to 07:00
    hours_to: str = ""
    min_free_gb: int = 2

    # --- after a download ---
    after: str = "nothing"  # nothing | open | reveal | copy
    run_after: str = ""  # a command, with {file} for the path

    # --- power users ---
    ytdlp_args: str = ""
    gdl_args: str = ""

    # --- behaviour ---
    clipboard: str = "off"  # off | ask | auto
    hotkey: bool = True  # Ctrl+Alt+D downloads the copied link from anywhere
    notify: bool = True
    sound: bool = False
    close_to_tray: bool = False
    autostart: bool = False
    auto_update: bool = True
    ytdlp_channel: str = "stable"  # stable | nightly
    self_update: bool = True
    # The preview's own player: the picture height it asks for, or sound alone, or
    # nothing at all. A slow computer stutters on the bigger ones.
    preview_playback: str = "360"  # 360 | 240 | 144 | sound | off
    last_update: float = 0.0

    @classmethod
    def load(cls, raw: object) -> Self:
        """Build options from stored JSON, keeping each default whose value does not fit."""
        values = store.record(raw)
        defaults = cls()
        good: dict[str, Any] = {}
        for field in fields(cls):
            if field.name in values:
                value = coerce(values[field.name], getattr(defaults, field.name))
                if value is not None:
                    good[field.name] = value
        return cls(**good)

    def dump(self) -> dict[str, object]:
        """Return the options as JSON-ready data."""
        return asdict(self)

    def but(self, changes: Mapping[str, object]) -> Self:
        """Return a copy with some values changed, each checked like a stored one."""
        return type(self).load({**self.dump(), **changes})


def coerce(value: object, default: object) -> object | None:
    """Return `value` as the type of `default`, or None when it cannot be one."""
    if isinstance(default, bool):
        return value if isinstance(value, bool) else None
    if isinstance(default, int | float):
        if isinstance(value, bool) or not isinstance(value, int | float | str):
            return None
        try:
            return type(default)(value)
        except ValueError:
            return None
    return value if isinstance(value, str) else None


DEFAULTS = Options().dump()

# What a preset may set: the shape of a download, never where it goes or how
# Keepsake behaves.
PRESET_KEYS = frozenset(
    {
        "mode",
        "quality",
        "container",
        "codec",
        "prefer_sdr",
        "always_plays",
        "audio_format",
        "audio_quality",
        "audio_lang",
        "subs",
        "sub_langs",
        "auto_subs",
        "strip_metadata",
        "embed_thumbnail",
        "square_cover",
        "embed_metadata",
        "embed_chapters",
        "split_chapters",
        "write_thumbnail",
        "write_description",
        "write_info_json",
        "write_comments",
        "sponsorblock",
        "sponsor_categories",
        "music",
        "archive",
        "live_from_start",
        "wait_for_live",
        "skip_shorts",
        "skip_live",
        "skip_members",
        "min_duration",
        "max_duration",
        "playlist_reverse",
        "template",
    }
)

# What one download may change from the preview, and nothing else.
PER_JOB_KEYS = frozenset(
    {
        "format",
        "items",
        "playlist",
        "section",
        "chapters",
        "mode",
        "rename",
        "folder",
        "ignore_archive",
    }
)

BUILT_IN_PRESETS: dict[str, dict[str, object]] = {
    "Best quality": {
        "mode": "auto",
        "quality": "best",
        "container": "mp4",
        "codec": "any",
        "prefer_sdr": False,
        "always_plays": False,
    },
    "Plays everywhere (1080p H.264 MP4)": {
        "mode": "video",
        "quality": "1080",
        "container": "mp4",
        "codec": "h264",
        "prefer_sdr": True,
        "always_plays": True,
    },
    "Phone (720p)": {"mode": "video", "quality": "720", "container": "mp4", "codec": "h264"},
    "4K archive (MKV, everything kept)": {
        "mode": "video",
        "quality": "best",
        "container": "mkv",
        "codec": "any",
        "prefer_sdr": False,
        "subs": "embed",
        "strip_metadata": False,
        "embed_thumbnail": True,
        "embed_metadata": True,
        "embed_chapters": True,
        "write_info_json": True,
        "write_description": True,
        "archive": True,
    },
    "Music (MP3 320, tagged, square covers)": {
        "mode": "audio",
        "audio_format": "mp3",
        "audio_quality": "320K",
        "strip_metadata": False,
        "music": True,
        "embed_thumbnail": True,
        "square_cover": True,
        "embed_metadata": True,
    },
    "Lossless music (FLAC)": {
        "mode": "audio",
        "audio_format": "flac",
        "audio_quality": "0",
        "strip_metadata": False,
        "music": True,
        "embed_thumbnail": True,
        "square_cover": True,
        "embed_metadata": True,
    },
    "Podcast (MP3 128, sponsors cut)": {
        "mode": "audio",
        "audio_format": "mp3",
        "audio_quality": "128K",
        "sponsorblock": "remove",
        "strip_metadata": False,
        "embed_metadata": True,
    },
    "Livestream from the start": {
        "mode": "video",
        "live_from_start": True,
        "wait_for_live": True,
        "container": "mkv",
    },
    "Transcript only": {"mode": "transcript", "auto_subs": True},
    "Pictures only": {"mode": "images"},
}


def preset_values(options: Options) -> dict[str, object]:
    """Return the part of the options a preset records."""
    return {key: value for key, value in options.dump().items() if key in PRESET_KEYS}


def with_preset(options: Options, values: Mapping[str, object]) -> Options:
    """Apply a preset's values, ignoring anything a preset may not set."""
    return options.but({k: v for k, v in values.items() if k in PRESET_KEYS})


def per_job(options: Options, extra: object) -> Options:
    """Apply what a single download may override, from the preview."""
    if not isinstance(extra, Mapping):
        return options
    changes = cast("Mapping[str, object]", extra)
    return options.but({k: v for k, v in changes.items() if k in PER_JOB_KEYS})
