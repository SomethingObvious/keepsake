"""Turning options into yt-dlp and gallery-dl command lines.

Each function builds one concern's arguments, so a download's command line is
the sum of small, separately tested pieces rather than one long function.
"""

import re
import shlex
from collections.abc import Sequence
from pathlib import Path

from keepsake import paths
from keepsake.cookies import Credentials, arguments
from keepsake.links import gallery_name
from keepsake.options import Options

YTDLP = [paths.PYTHON, "-m", "yt_dlp"]
GALLERY = [paths.PYTHON, "-m", "gallery_dl"]

# What yt-dlp prints for Keepsake to read, each line tagged so it can never be
# mistaken for the tool's own output.
PROGRESS = (
    "KEEPSAKE-PROG %(progress.downloaded_bytes)s %(progress.total_bytes)s "
    "%(progress.total_bytes_estimate)s %(progress.speed)s %(progress.eta)s"
)
STAGE = "KEEPSAKE-PP %(progress.postprocessor)s %(progress.status)s"
META = (
    "KEEPSAKE-META %(.{id,extractor_key,title,thumbnail,duration,webpage_url,uploader,channel,"
    "playlist_title,playlist_index,playlist_count,live_status})j"
)
# The file, and the others yt-dlp wrote for it: chapters where it cut them,
# thumbnails and subtitles where they were before being moved beside it.
WROTE = "KEEPSAKE-FILE %(.{filepath,timestamp,chapters,thumbnails,requested_subtitles})j"

# Embedding into webm or wav is not skipped by yt-dlp: it fails the whole
# download after the download has finished (measured), so it is left out.
EMBEDS_COVER_IN = ("mp4", "mkv")
SQUARE = "ThumbnailsConvertor+FFmpeg_o:-vf crop=\"'if(gt(ih,iw),iw,ih)':'if(gt(iw,ih),ih,iw)'\""
CODECS = {"h264": "vcodec:h264", "h265": "vcodec:h265", "vp9": "vcodec:vp9", "av1": "vcodec:av01"}
FITS = {"mp4": "ext:mp4:m4a", "webm": "ext:webm:webm"}
RELATIVE_DATE = re.compile(r"^(now|today|yesterday)([+-]\d+(day|week|month|year)s?)?$")
FULL_DATE = re.compile(r"^(\d{4})-?(\d{2})-?(\d{2})$")
CLOCK = re.compile(r"^(?:(\d+):)?(\d+):(\d{1,2})$")


def split_args(text: str) -> list[str]:
    """Split the extra-arguments box, keeping Windows paths' backslashes."""
    return shlex.split(text.replace("\\", "\\\\")) if text.strip() else []


def seconds(text: str) -> int | None:
    """Read a duration typed as 90, 1:30 or 1:02:03."""
    text = text.strip()
    if text.isdigit():
        return int(text)
    match = CLOCK.match(text)
    if not match:
        return None
    hours, minutes, secs = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + secs


def ytdlp_date(text: str) -> str | None:
    """Read a date typed as 2026-09-01, 20260901 or now-7days."""
    text = text.strip().lower().replace(" ", "")
    if RELATIVE_DATE.match(text):
        return text
    match = FULL_DATE.match(text)
    return "".join(match.groups()) if match else None


def filter_text(value: str) -> str:
    """Quote a user's words for a yt-dlp match filter, where & separates conditions."""
    return value.replace("\\", "\\\\").replace("&", "\\&").replace("'", "\\'")


def match_filters(o: Options) -> list[str]:
    """Return the conditions a video must meet to be downloaded."""
    rules: list[str] = []
    if o.skip_shorts:
        rules.append("original_url!*=/shorts/")
    if o.skip_live:
        rules += ["!is_live", "live_status!=is_upcoming", "live_status!=was_live"]
    if o.skip_members:
        rules += ["availability!=subscriber_only", "availability!=premium_only"]
    shortest, longest = seconds(o.min_duration), seconds(o.max_duration)
    if shortest is not None:
        rules.append(f"duration>={shortest}")
    if longest is not None:
        rules.append(f"duration<={longest}")
    if o.title_match.strip():
        rules.append(f"title~='(?i){filter_text(o.title_match.strip())}'")
    if o.title_skip.strip():
        rules.append(f"title!~='(?i){filter_text(o.title_skip.strip())}'")
    return rules


def filter_args(o: Options) -> list[str]:
    """Return the playlist and channel filters as arguments."""
    args: list[str] = []
    rules = match_filters(o)
    if rules:
        args += ["--match-filters", " & ".join(rules)]
    for flag, value in (("--dateafter", o.date_after), ("--datebefore", o.date_before)):
        date = ytdlp_date(value)
        if date:
            args += [flag, date]
    if o.max_items.strip().isdigit():
        args += ["--max-downloads", o.max_items.strip()]
    return args


def video_sort(o: Options) -> str:
    """Return how to choose between formats: resolution first, the rest breaks ties."""
    parts = [f"res:{o.quality}" if o.quality.isdigit() else "res"]
    if o.always_plays:
        # Here H.264 outranks resolution: a file that plays is the point.
        parts.insert(0, "vcodec:h264")
    elif o.codec in CODECS:
        parts.append(CODECS[o.codec])
    if o.prefer_sdr:
        parts.append("hdr:sdr")
    # Steering by container picks YouTube's 128k AAC over its better Opus;
    # at best quality the merge takes either without re-encoding.
    if o.container in FITS and o.quality != "best":
        parts.append(FITS[o.container])
    return ",".join(parts)


def format_args(o: Options) -> list[str]:
    """Return which streams to take and what to wrap them in."""
    if o.mode == "audio":
        args = ["-f", o.format or "ba/b", "-x", "--audio-quality", o.audio_quality]
        return args + (["--audio-format", o.audio_format] if o.audio_format != "best" else [])
    if o.format:
        spec = o.format
    elif o.audio_lang == "all":
        spec = "bv*+mergeall[vcodec=none]/b"
    elif o.audio_lang:
        spec = f"bv*+ba[language^={o.audio_lang}]/bv*+ba/b"
    else:
        spec = "bv*+ba/b"
    args = ["-f", spec, "-S", video_sort(o)]
    if o.audio_lang == "all":
        args += ["--audio-multistreams", "--merge-output-format", "mkv"]
    elif o.container != "original":
        args += ["--merge-output-format", o.container]
    return args


def subtitle_args(o: Options) -> list[str]:
    """Return subtitle arguments, or those for a transcript."""
    if o.mode == "transcript":
        args = ["--skip-download", "--write-subs", "--sub-langs", o.sub_langs or "en.*"]
        return [*args, "--write-auto-subs", "--convert-subs", "srt"]
    if o.mode == "audio" or o.subs == "off":
        return []
    args = ["--write-subs", "--sub-langs", o.sub_langs or "en.*"]
    if o.auto_subs:
        args.append("--write-auto-subs")
    return args + (["--embed-subs"] if o.subs == "embed" else ["--convert-subs", "srt"])


def cover_fits(o: Options) -> bool:
    """Return whether cover art can go into the file this download will make."""
    if o.mode == "audio":
        return o.audio_format != "wav"
    return o.container in EMBEDS_COVER_IN and o.audio_lang != "all"


# What "Remove metadata and source" turns off: everything that would put
# words about a file into it, or beside it.
DESCRIBES = (
    "embed_thumbnail",
    "square_cover",
    "embed_metadata",
    "embed_chapters",
    "music",
    "write_description",
    "write_info_json",
    "write_comments",
    "write_metadata",
)


def without_metadata(o: Options) -> Options:
    """Return the options with nothing that describes a file, when that was asked for."""
    return o.but(dict.fromkeys(DESCRIBES, False)) if o.strip_metadata else o


# Everything Keepsake itself could re-encode: best quality never does.
LOSSY_UGOIRA = frozenset({"webm", "mp4", "gif"})


def untouched(o: Options) -> Options:
    """Return the options with nothing re-encoded, at best quality."""
    if o.quality != "best":
        return o
    ugoira = "copy" if o.ugoira in LOSSY_UGOIRA else o.ugoira
    return o.but({"always_plays": False, "precise_cuts": False, "ugoira": ugoira})


def effective(o: Options) -> Options:
    """Return what a download actually does with these options."""
    return untouched(without_metadata(o))


def keep_args(o: Options) -> list[str]:
    """Return what to embed in the file and what to write beside it."""
    args: list[str] = []
    if o.embed_thumbnail and cover_fits(o):
        lossless = "png" if o.quality == "best" else "jpg"
        args += ["--embed-thumbnail", "--convert-thumbnails", lossless]
        if o.music and o.square_cover:
            args += ["--ppa", SQUARE]
    flags = (
        (o.embed_metadata or o.music, "--embed-metadata"),
        (o.embed_chapters, "--embed-chapters"),
        (o.split_chapters, "--split-chapters"),
        (o.write_thumbnail, "--write-thumbnail"),
        (o.write_description, "--write-description"),
        (o.write_info_json or o.write_comments, "--write-info-json"),
        (o.write_comments, "--write-comments"),
        (o.restrict_names, "--restrict-filenames"),
    )
    args += [flag for wanted, flag in flags if wanted]
    if o.write_comments and o.max_comments.strip().isdigit():
        count = o.max_comments.strip()
        args += ["--extractor-args", f"youtube:max_comments={count},all,100;comment_sort=top"]
    return args


def music_args(o: Options) -> list[str]:
    """Return tagging that makes a playlist read as an album in a music player."""
    if not o.music:
        return []
    return [
        "--parse-metadata",
        "%(artist,creator,uploader|)s:%(meta_artist)s",
        "--parse-metadata",
        "title:(?P<meta_artist>.+?) - (?P<meta_title>.+)",
        "--replace-in-metadata",
        "meta_artist",
        r"\s*-\s*Topic$",
        "",
        "--parse-metadata",
        "%(album,playlist_title|)s:%(meta_album)s",
        "--parse-metadata",
        "%(track_number,playlist_index|)s:%(meta_track)s",
    ]


def clip_args(o: Options) -> list[str]:
    """Return which parts of a video to take: time ranges, or chapters picked in the preview."""
    args: list[str] = []
    for part in (piece.strip() for piece in o.section.split(",")):
        if part:
            args += ["--download-sections", part if part.startswith("*") else "*" + part]
    for title in (line.strip() for line in o.chapters.splitlines()):
        if title:
            args += ["--download-sections", f"^{re.escape(title)}$"]
    if args and o.precise_cuts:
        args.append("--force-keyframes-at-cuts")
    return args


def playlist_args(o: Options) -> list[str]:
    """Return how much of a playlist to take, and in which order."""
    args = ["--yes-playlist" if o.playlist else "--no-playlist"]
    if o.items.strip():
        args += ["-I", o.items.strip()]
    if o.playlist_reverse:
        args.append("--playlist-reverse")
    return args


def live_args(o: Options) -> list[str]:
    """Return how to handle a livestream or a premiere that has not started."""
    args: list[str] = []
    if o.live_from_start:
        args.append("--live-from-start")
    if o.wait_for_live:
        args += ["--wait-for-video", "30-300"]
    return args


def politeness_args(o: Options, *, gallery: bool) -> list[str]:
    """Return the pauses that keep a site from rate-limiting this machine."""
    if o.politeness == "off":
        return []
    if gallery:
        careful = ["--sleep", "2-5", "--sleep-request", "1-2", "--sleep-429", "120"]
        return careful if o.politeness == "careful" else ["--sleep-429", "60"]
    if o.politeness == "careful":
        return [
            "--sleep-requests",
            "0.75",
            "--sleep-interval",
            "10",
            "--max-sleep-interval",
            "20",
            "--sleep-subtitles",
            "5",
        ]
    return ["--sleep-requests", "0.25"] if o.playlist else []


def network_args(o: Options) -> list[str]:
    """Return retries, proxy and speed limit, which both tools spell the same way."""
    args = ["-R", str(o.retries)]
    if o.proxy.strip():
        args += ["--proxy", o.proxy.strip()]
    if o.rate.strip():
        args += ["-r", o.rate.strip()]
    return args


def runtime_args() -> list[str]:
    """Return the JavaScript runtime YouTube's player challenges need.

    yt-dlp enables Deno by itself; Node has to be named.
    """
    node = paths.tool("node")
    if paths.tool("deno") != "deno" or node == "node":
        return []
    return ["--js-runtimes", f"node:{node}"]


def plugin_args() -> list[str]:
    """Return yt-dlp's plugin folder, when there is anything in it."""
    folder = paths.DATA / "yt-dlp-plugins"
    return ["--plugin-dirs", str(folder)] if folder.is_dir() and any(folder.iterdir()) else []


def folder_for(o: Options, *, gallery: bool = False) -> str:
    """Return where this download goes: videos, sound, pictures and transcripts each have one."""
    if gallery or o.mode == "images":
        chosen = o.picture_folder
    elif o.mode == "audio":
        chosen = o.audio_folder
    elif o.mode == "transcript":
        chosen = o.text_folder
    else:
        chosen = o.folder
    return chosen.strip() or o.folder


def output_args(o: Options) -> list[str]:
    """Return where files go and what they are called."""
    template = ("%(extractor_key)s/" if o.by_site else "") + o.template
    if o.live_from_start or o.wait_for_live:
        # Two recordings of the same stream would otherwise overwrite each other.
        template = template.replace(".%(ext)s", " %(epoch)s.%(ext)s")
    args = ["-P", folder_for(o), "-o", template, "--trim-filenames", str(o.trim_names)]
    if o.rename.strip():
        new = o.rename.strip().replace("\\", "\\\\")
        args += ["--replace-in-metadata", "title", ".+", new]
    return args


def archive_args(o: Options, archive: Path | None) -> list[str]:
    """Return how repeats are handled."""
    if o.ignore_archive:
        return ["--no-download-archive", "--force-overwrites"]
    if archive:
        return ["--download-archive", str(archive)]
    if o.archive:
        return ["--download-archive", str(paths.DATA / "yt-dlp-archive.txt")]
    return []


def after_args(o: Options, *, gallery: bool) -> list[str]:
    """Return a command the user wants run on each finished file."""
    command = o.run_after.strip().replace("{file}", "{}")
    if not command:
        return []
    return ["--exec", command] if gallery else ["--exec", f"after_move:{command}"]


def ytdlp_command(
    o: Options,
    url: str,
    credentials: Credentials | None,
    *,
    archive: Path | None = None,
    extra: Sequence[str] = (),
) -> list[str]:
    """Return the whole yt-dlp command line for one download."""
    o = effective(o)
    watch = [
        "--newline",
        "--color",
        "never",
        "--progress",
        "--progress-template",
        "download:" + PROGRESS,
        "--progress-template",
        "postprocess:" + STAGE,
        "--print",
        "before_dl:" + META,
        "--print",
        "after_move:" + WROTE,
        "--no-simulate",
        "--no-quiet",
    ]
    return [
        *YTDLP,
        *watch,
        *output_args(o),
        *format_args(o),
        *subtitle_args(o),
        *keep_args(o),
        *music_args(o),
        *clip_args(o),
        *playlist_args(o),
        *live_args(o),
        *filter_args(o),
        *(["--sponsorblock-mark", "all"] if o.sponsorblock == "mark" else []),
        *(
            ["--sponsorblock-remove", o.sponsor_categories or "sponsor"]
            if o.sponsorblock == "remove"
            else []
        ),
        *archive_args(o, archive),
        *([] if o.file_date == "upload" else ["--no-mtime"]),
        "-N",
        str(o.fragments),
        "--fragment-retries",
        str(o.retries),
        *(["--impersonate", o.impersonate] if o.impersonate else []),
        *politeness_args(o, gallery=False),
        *network_args(o),
        *runtime_args(),
        *plugin_args(),
        *after_args(o, gallery=False),
        *arguments(credentials),
        *extra,
        *split_args(o.ytdlp_args),
        "--",
        url,
    ]


def gallery_command(
    o: Options,
    url: str,
    credentials: Credentials | None,
    *,
    archive: Path | None = None,
    extra: Sequence[str] = (),
) -> list[str]:
    """Return the whole gallery-dl command line for one download."""
    o = effective(o)
    base = folder_for(o, gallery=True)
    # By site: gallery-dl's own folders. Otherwise one folder per gallery.
    where = ["-d", base] if o.by_site else ["-D", str(Path(base) / gallery_name(url))]
    args = [*GALLERY, *where]
    for flag, value in (("--range", o.range), ("--filter", o.gallery_filter)):
        if value.strip():
            args += [flag, value.strip()]
    if o.write_metadata:
        args.append("--write-metadata")
    if o.zip:
        args.append("--zip")
    if o.ugoira != "off":
        args += ["--ugoira", o.ugoira]
    if o.ignore_archive:
        args.append("--no-skip")
    elif archive or o.archive:
        args += ["--download-archive", str(archive or paths.DATA / "gallery-dl-archive.sqlite3")]
    args += ["--mtime", "date"] if o.file_date == "upload" else ["--no-mtime"]
    return [
        *args,
        *politeness_args(o, gallery=True),
        *network_args(o),
        *after_args(o, gallery=True),
        *arguments(credentials),
        *extra,
        *split_args(o.gdl_args),
        "--",
        url,
    ]


def range_size(text: str) -> int | None:
    """Return how many files a gallery range allows, when it is a plain a-b."""
    match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", text)
    return int(match[2]) - int(match[1]) + 1 if match else None


STAGE_NAMES = {
    "FFmpegMerger": "Merging video and audio",
    "FFmpegExtractAudio": "Extracting audio",
    "EmbedThumbnail": "Embedding cover art",
    "FFmpegThumbnailsConvertor": "Converting cover art",
    "FFmpegMetadata": "Writing tags",
    "MetadataParser": "Reading tags",
    "FFmpegEmbedSubtitle": "Embedding subtitles",
    "FFmpegSubtitlesConvertor": "Converting subtitles",
    "SponsorBlock": "Asking SponsorBlock",
    "ModifyChapters": "Cutting segments",
    "FFmpegSplitChapters": "Splitting chapters",
    "FFmpegVideoRemuxer": "Remuxing",
    "FFmpegVideoConvertor": "Converting",
    "MoveFilesAfterDownload": "Finishing",
    "FFmpegCopyStream": "Copying streams",
    "Exec": "Running your command",
}


def stage_name(key: str) -> str:
    """Return a plain name for a yt-dlp post-processing step."""
    if key in STAGE_NAMES:
        return STAGE_NAMES[key]
    if key.startswith("FFmpegFixup"):
        return "Fixing up the file"
    return re.sub(r"(?<!^)(?=[A-Z])", " ", key.removeprefix("FFmpeg")).capitalize()
