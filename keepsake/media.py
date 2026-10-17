"""FFmpeg work on files already downloaded, and turning subtitles into a transcript."""

import functools
import glob
import hashlib
import io
import json
import os
import re
import threading
import zipfile
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageOps, ImageSequence

from keepsake import paths, process, store

# Hardware first: a graphics card encodes H.264 many times faster than the
# processor, and an encoder that is listed is not always one that works, so each
# is tried on a single frame before it is trusted.
HARDWARE = ("h264_nvenc", "h264_qsv", "h264_amf")
PLAYS_EVERYWHERE_VIDEO = frozenset({"h264"})
PLAYS_EVERYWHERE_AUDIO = frozenset({"aac", "mp3", ""})
THUMB = 352  # two pixels for each of a library tile's 176, for scaled-up screens
VIDEO_INTRO = 8  # seconds: a video shorter than this shows its first frame
# The library asks for every tile on screen at once. Two at a time keeps a slow
# computer usable while they are made, and each is made only once.
DRAWING = threading.BoundedSemaphore(2)


def ffmpeg() -> str:
    """Return the ffmpeg program."""
    return paths.tool("ffmpeg")


@functools.cache
def h264_encoder() -> str:
    """Return the fastest H.264 encoder that actually works on this machine."""
    for encoder in HARDWARE:
        probe = [
            ffmpeg(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=black:s=256x256:d=0.1",
            "-frames:v",
            "1",
            "-c:v",
            encoder,
            "-f",
            "null",
            "-",
        ]
        try:
            if process.run(probe, timeout=20).returncode == 0:
                return encoder
        except OSError:
            break
    return "libx264"


def codecs(path: Path) -> tuple[str, str]:
    """Return the video and audio codec names of a file, empty where there is none."""
    command = [
        paths.tool("ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,codec_name",
        "-of",
        "json",
        str(path),
    ]
    try:
        found = json.loads(process.run(command, timeout=60).stdout or "{}")
    except (OSError, ValueError):
        return "", ""
    streams = [store.record(stream) for stream in store.items(store.record(found).get("streams"))]

    def first(kind_of: str) -> str:
        return next(
            (str(s.get("codec_name", "")) for s in streams if s.get("codec_type") == kind_of), ""
        )

    return first("video"), first("audio")


def plays_everywhere(path: Path) -> bool:
    """Return whether a video is already H.264 with AAC or MP3 sound in an MP4."""
    video, audio = codecs(path)
    return (
        path.suffix.lower() == ".mp4"
        and video in PLAYS_EVERYWHERE_VIDEO
        and audio in PLAYS_EVERYWHERE_AUDIO
    )


def duration(path: Path) -> float | None:
    """Return a file's length in seconds."""
    command = [
        paths.tool("ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        return float(process.run(command, timeout=60).stdout.strip())
    except (OSError, ValueError):
        return None


def beside(path: Path, note: str, suffix: str) -> Path:
    """Return a new name beside a file, never one already there, held with an empty file.

    Two clips of one video run side by side, so a name only checked as free
    could be taken by the other before either is written.
    """
    number = 1
    while True:
        candidate = path.with_name(
            f"{path.stem} ({note}{f' {number}' if number > 1 else ''}){suffix}"
        )
        try:
            candidate.touch(exist_ok=False)
        except FileExistsError:
            number += 1
        else:
            return candidate


def compatible_command(source: Path, target: Path) -> list[str]:
    """Return a re-encode to H.264 and AAC in an MP4 that starts playing at once."""
    encoder = h264_encoder()
    quality = ["-crf", "20", "-preset", "medium"] if encoder == "libx264" else ["-cq", "21"]
    return [
        ffmpeg(),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        encoder,
        *quality,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-progress",
        "pipe:1",
        "-nostats",
        str(target),
    ]


# Each sound format with the codec it already holds, which is copied as it is, and how to
# encode anything else into it. FLAC is always encoded: that is lossless, and a copied one
# keeps the whole source's length in its header, so a clip of it claims to be the full song.
SOUND_FORMATS: dict[str, tuple[str | None, list[str]]] = {
    "mp3": ("mp3", ["libmp3lame", "-q:a", "0"]),
    "m4a": ("aac", ["aac", "-b:a", "256k"]),
    "opus": ("opus", ["libopus", "-b:a", "160k"]),
    "flac": (None, ["flac"]),
    "wav": ("pcm_s16le", ["pcm_s16le"]),
}


# Longer than any codec's own start delay. A lead-in shorter than this is not worth a re-encode.
CODEC_DELAY = 0.1


def lead_in(path: Path) -> bool:
    """Return whether the sound starts well before zero, or might.

    A keyframe cut keeps a second or so of sound before the cut and hides it
    with an edit list. A copy into Opus, WebM or FLAC drops the list and brings
    that second back, so such sound has to be decoded. The few milliseconds a
    codec starts early by (6.5 for Opus, under 50 for AAC) copy fine.
    """
    command = [
        paths.tool("ffprobe"),
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-read_intervals",
        "%+#1",
        "-show_entries",
        "packet=pts_time",
        "-of",
        "csv=p=0",
        str(path),
    ]
    try:
        return float(process.run(command, timeout=60).stdout.split(",")[0]) < -CODEC_DELAY
    except (OSError, ValueError):
        return True


def audio_command(source: Path, target: Path, start: float = 0, end: float = 0) -> list[str]:
    """Return the sound, or `start` to `end` seconds of it, in the target's format.

    It is re-encoded only if it has to be.
    """
    holds, encode = SOUND_FORMATS[target.suffix.lower().lstrip(".")]
    # After the input: every packet of sound can start a cut, and a copy seeking before it
    # starts at the cluster before, seconds early in a WebM.
    span = ["-ss", f"{start:.3f}", "-to", f"{end:.3f}"] if end > start else []
    return [
        ffmpeg(),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        *span,
        "-vn",
        "-c:a",
        *(["copy"] if codecs(source)[1] == holds and not lead_in(source) else encode),
        "-progress",
        "pipe:1",
        "-nostats",
        str(target),
    ]


def trim_command(source: Path, target: Path, start: float, end: float, *, exact: bool) -> list[str]:
    """Return a cut from `start` to `end` seconds: instant, or exact to the frame."""
    span = ["-ss", f"{start:.3f}", "-to", f"{end:.3f}"]
    if exact:
        codec = ["-c:v", h264_encoder(), "-c:a", "aac"]
        return [
            ffmpeg(),
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            *span,
            *codec,
            "-progress",
            "pipe:1",
            "-nostats",
            str(target),
        ]
    # A video can only start at a keyframe, so it seeks to the one before. Sound alone cuts
    # exactly when the seek comes after the input.
    sound_only = not codecs(source)[0]
    return [
        ffmpeg(),
        "-hide_banner",
        "-y",
        *([] if sound_only else span),
        "-i",
        str(source),
        *(span if sound_only else []),
        *(["-c:a", "flac"] if target.suffix.lower() == ".flac" else ["-c", "copy"]),
        "-avoid_negative_ts",
        "make_zero",
        "-progress",
        "pipe:1",
        "-nostats",
        str(target),
    ]


def gif_command(source: Path, target: Path, start: float, end: float) -> list[str]:
    """Return a GIF of a stretch of video, with a palette made for it."""
    graph = (
        "fps=15,scale=540:-1:flags=lanczos,split[a][b];"
        "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a"
    )
    return [
        ffmpeg(),
        "-hide_banner",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-to",
        f"{end:.3f}",
        "-i",
        str(source),
        "-vf",
        graph,
        "-progress",
        "pipe:1",
        "-nostats",
        str(target),
    ]


TIMING = re.compile(r"^(\d{2}:)?\d{2}:\d{2}[,.]\d{3} --> ")
# WebVTT's header and block lines, which are not words anybody said.
HEADERS = ("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE", "REGION")
TAG = re.compile(r"<[^>]+>|\{[^}]+\}")


def transcript(subtitles: str) -> str:
    """Return the words of an SRT file as plain paragraphs.

    Auto-generated captions roll: each cue repeats the line before it with a
    few words added, so a line already said is not said again.
    """
    lines: list[str] = []
    for raw in subtitles.splitlines():
        line = TAG.sub("", raw).strip()
        if not line or line.isdigit() or TIMING.match(line) or line.startswith(HEADERS):
            continue
        if lines and line == lines[-1]:
            continue
        lines.append(line)
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text).strip()
    # A paragraph every few sentences, so it reads as prose rather than one wall.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return "\n\n".join(" ".join(sentences[i : i + 5]) for i in range(0, len(sentences), 5)) + "\n"


def scrub_command(source: Path, target: Path) -> list[str]:
    """Return a copy of a video or sound file with nothing about what it is or where it came from.

    It keeps pictures that are not cover art ("V"), sound and subtitles, and
    leaves tags, chapters, covers, attachments and data tracks behind;
    bitexact keeps ffmpeg from signing its own version in.
    """
    no_id3 = ["-id3v2_version", "0", "-write_id3v1", "0"] if target.suffix.lower() == ".mp3" else []
    return [
        ffmpeg(),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:V?",
        "-map",
        "0:a?",
        "-map",
        "0:s?",
        "-c",
        "copy",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-fflags",
        "+bitexact",
        "-flags:v",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        *no_id3,
        "-progress",
        "pipe:1",
        "-nostats",
        str(target),
    ]


MARKER, START_OF_SCAN, COMMENT = 0xFF, 0xDA, 0xFE
FIRST_APP, LAST_APP = 0xE0, 0xEF
# The only application segments that are part of the picture: JFIF's header,
# the colour profile, and Adobe's colour-transform marker (without it a CMYK
# JPEG decodes in the wrong colours).
JPEG_KEEPS = {0xE0: b"JFIF\0", 0xE2: b"ICC_PROFILE\0", 0xEE: b"Adobe"}


def strip_jpeg(data: bytes) -> bytes:
    """Drop EXIF, XMP, IPTC, comments and embedded previews, byte for byte, without re-encoding."""
    if not data.startswith(b"\xff\xd8"):
        return data
    kept, at = bytearray(data[:2]), 2
    while at + 4 <= len(data) and data[at] == MARKER:
        marker = data[at + 1]
        if marker == START_OF_SCAN:
            break  # the picture itself follows, and is copied as it is
        if marker == MARKER:  # padding before a marker
            at += 1
            continue
        end = at + 2 + int.from_bytes(data[at + 2 : at + 4], "big")
        body = data[at + 4 : end]
        app = FIRST_APP <= marker <= LAST_APP
        known = marker in JPEG_KEEPS and body.startswith(JPEG_KEEPS[marker])
        if marker != COMMENT and (not app or known):
            kept += data[at:end]
        at = end
    return bytes(kept + data[at:])


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Ancillary chunks that shape the picture. Every other ancillary chunk (tEXt,
# zTXt, iTXt, eXIf, tIME) is words about it; critical chunks always stay.
PNG_KEEPS = frozenset(
    {
        b"tRNS",
        b"gAMA",
        b"cHRM",
        b"sRGB",
        b"iCCP",
        b"sBIT",
        b"pHYs",
        b"bKGD",
        b"acTL",
        b"fcTL",
        b"fdAT",
        b"cICP",
        b"mDCV",
        b"cLLI",
    }
)


def strip_png(data: bytes) -> bytes:
    """Drop text, EXIF and timestamps from a PNG, keeping every chunk the picture needs."""
    if not data.startswith(PNG_SIGNATURE):
        return data
    kept, at = bytearray(PNG_SIGNATURE), len(PNG_SIGNATURE)
    while at + 12 <= len(data):
        name = data[at + 4 : at + 8]
        end = at + 12 + int.from_bytes(data[at : at + 4], "big")
        if name[:1].isupper() or name in PNG_KEEPS:
            kept += data[at:end]
        at = end
    return bytes(kept)


WEBP_WORDS = (b"EXIF", b"XMP ")
WEBP_EXIF_AND_XMP_FLAGS = 0x08 | 0x04


def strip_webp(data: bytes) -> bytes:
    """Drop the EXIF and XMP chunks of a WebP, and the header's flags that announce them."""
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return data
    chunks: list[bytes] = []
    at = 12
    while at + 8 <= len(data):
        name = data[at : at + 4]
        size = int.from_bytes(data[at + 4 : at + 8], "little")
        end = at + 8 + size + (size & 1)
        chunk = bytearray(data[at:end])
        if name == b"VP8X":
            chunk[8] &= ~WEBP_EXIF_AND_XMP_FLAGS & 0xFF
        if name not in WEBP_WORDS:
            chunks.append(bytes(chunk))
        at = end
    body = b"WEBP" + b"".join(chunks)
    return b"RIFF" + len(body).to_bytes(4, "little") + body


GIF_LOOPS = (b"NETSCAPE2.0", b"ANIMEXTS1.0")
GIF_KEEPS = (0xF9, 0x01)  # frame timing and transparency, and text drawn on the picture
GIF_IMAGE, GIF_EXTENSION, GIF_TRAILER, GIF_APPLICATION = 0x2C, 0x21, 0x3B, 0xFF


def colour_table(flags: int) -> int:
    """Return the size of the colour table a GIF's flags announce."""
    return 3 << ((flags & 7) + 1) if flags & 0x80 else 0


def after_blocks(data: bytes, at: int) -> int:
    """Return where a run of GIF data sub-blocks ends."""
    while data[at]:
        at += data[at] + 1
    return at + 1


def strip_gif(data: bytes) -> bytes:
    """Drop comments and application blocks other than looping, keeping every frame as it is."""
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        return data
    at = 13 + colour_table(data[10])
    kept = bytearray(data[:at])
    while data[at] != GIF_TRAILER:
        if data[at] == GIF_IMAGE:  # descriptor, colour table, LZW code size, then the data
            end = after_blocks(data, at + 10 + colour_table(data[at + 9]) + 1)
            kept += data[at:end]
        elif data[at] == GIF_EXTENSION:
            label, end = data[at + 1], after_blocks(data, at + 2)
            loops = label == GIF_APPLICATION and data[at + 3 : at + 14] in GIF_LOOPS
            if label in GIF_KEEPS or loops:
                kept += data[at:end]
        else:
            message = "not a block a GIF can hold"
            raise ValueError(message)
        at = end
    return bytes(kept + b";")


type Box = tuple[bytes, int, int, int]  # type, start, payload start, end


def boxes(data: bytes, start: int, end: int) -> list[Box]:
    """Return the ISO boxes between two offsets, as AVIF, HEIC and JPEG XL files hold them."""
    found: list[Box] = []
    at = start
    while at + 8 <= end:
        size, payload = int.from_bytes(data[at : at + 4], "big"), at + 8
        if size == 1:  # a 64-bit size follows the type
            size, payload = int.from_bytes(data[at + 8 : at + 16], "big"), at + 16
        elif size == 0:  # to the end
            size = end - at
        if size < payload - at or at + size > end:
            message = "a box runs past its end"
            raise ValueError(message)
        found.append((data[at + 4 : at + 8], at, payload, at + size))
        at += size
    return found


# Box versions that change the layout: an item entry carries its type from
# version 2 (and a 32-bit id from 3); an item list counts in 32 bits from 2.
TYPED_ENTRY = WIDE_LIST = 2


def number(data: bytes, at: int, width: int) -> int:
    """Read a big-endian number of `width` bytes (none is zero)."""
    return int.from_bytes(data[at : at + width], "big")


def metadata_items(data: bytes, start: int, end: int) -> dict[int, bytes]:
    """Return the Exif and XMP items an 'iinf' box lists: id to b"Exif" or b"mime"."""
    at = start + 4 + (2 if data[start] == 0 else 4)  # version and flags, then the count
    found: dict[int, bytes] = {}
    for name, _, payload, box_end in boxes(data, at, end):
        version = data[payload]
        if name != b"infe" or version < TYPED_ENTRY:
            continue
        width = 2 if version == TYPED_ENTRY else 4
        item = number(data, payload + 4, width)
        kind = data[payload + 4 + width + 2 : payload + 4 + width + 6]
        rest = data[payload + 4 + width + 6 : box_end]
        if kind == b"Exif" or (kind == b"mime" and b"xml" in rest):
            found[item] = kind
    return found


def item_extents(
    data: bytes, start: int, wanted: dict[int, bytes], idat: int
) -> list[tuple[bytes, int, int]]:
    """Return the kind of each wanted item and where its bytes are, from an 'iloc' box."""
    version, at = data[start], start + 4
    offset_size, length_size = data[at] >> 4, data[at] & 15
    base_size, index_size = data[at + 1] >> 4, (data[at + 1] & 15) if version else 0
    width = 2 if version < WIDE_LIST else 4
    count, at = number(data, at + 2, width), at + 2 + width
    found: list[tuple[bytes, int, int]] = []
    for _ in range(count):
        item, at = number(data, at, width), at + width
        method = 0
        if version:
            method, at = number(data, at, 2) & 15, at + 2
        base, at = number(data, at + 2, base_size), at + 2 + base_size  # after the reference index
        extents, at = number(data, at, 2), at + 2
        for _ in range(extents):
            at += index_size
            offset, at = number(data, at, offset_size), at + offset_size
            length, at = number(data, at, length_size), at + length_size
            if item in wanted and method in (0, 1) and length:
                found.append((wanted[item], (idat if method else 0) + base + offset, length))
    return found


# An Exif item that says nothing, yet still reads as Exif: libavif refuses to
# open a file whose Exif item is only zeros (measured). Its offset to the TIFF
# header, the header, and one directory with no entries in it.
EMPTY_EXIF = (0).to_bytes(4, "big") + b"MM\x00*" + (8).to_bytes(4, "big") + bytes(6)


def blank(kind: bytes, length: int) -> bytes:
    """Return what an Exif or XMP item is overwritten with: the same length, saying nothing."""
    if kind == b"Exif" and length >= len(EMPTY_EXIF):
        return EMPTY_EXIF + bytes(length - len(EMPTY_EXIF))
    return b" " * length if kind == b"mime" else bytes(length)


def strip_heif(data: bytes) -> bytes:
    """Blank the Exif and XMP items of an AVIF or HEIC in place, so no offset in it moves."""
    wiped = bytearray(data)
    for name, _, payload, end in boxes(data, 0, len(data)):
        if name != b"meta":
            continue
        children = {kind: (start, stop) for kind, _, start, stop in boxes(data, payload + 4, end)}
        if b"iinf" not in children or b"iloc" not in children:
            continue
        wanted = metadata_items(data, *children[b"iinf"])
        idat = children.get(b"idat", (0, 0))[0]
        for kind, offset, length in item_extents(data, children[b"iloc"][0], wanted, idat):
            if offset + length > len(data):
                message = "an item runs past the end of the file"
                raise ValueError(message)
            wiped[offset : offset + length] = blank(kind, length)
    return bytes(wiped)


JXL_SIGNATURE = b"\x00\x00\x00\x0cJXL \r\n\x87\n"
JXL_WORDS = (b"Exif", b"xml ", b"jumb")


def strip_jxl(data: bytes) -> bytes:
    """Drop the Exif, XMP and JUMBF boxes of a JPEG XL, compressed ('brob') ones too."""
    if not data.startswith(JXL_SIGNATURE):
        return data  # a bare codestream has nowhere to keep metadata
    kept = bytearray()
    for name, start, payload, end in boxes(data, 0, len(data)):
        inner = data[payload : payload + 4] if name == b"brob" else name
        if inner not in JXL_WORDS:
            kept += data[start:end]
    return bytes(kept)


def strip_tiff(data: bytes) -> bytes:
    """Save a TIFF again, losslessly and without its tags, only if every pixel survives."""
    with Image.open(io.BytesIO(data)) as picture:
        frames = [frame.copy() for frame in ImageSequence.Iterator(picture)]
        extra: dict[str, object] = {"compression": "tiff_adobe_deflate"}
        for key in ("icc_profile", "dpi"):
            if picture.info.get(key):
                extra[key] = picture.info[key]
    out = io.BytesIO()
    frames[0].save(out, "TIFF", save_all=True, append_images=frames[1:], **extra)
    with Image.open(io.BytesIO(out.getvalue())) as saved:
        same = [frame.tobytes() for frame in ImageSequence.Iterator(saved)]
    if same != [frame.tobytes() for frame in frames]:
        message = "saving it again would change pixels"
        raise ValueError(message)
    return out.getvalue()


def strip_zip(data: bytes) -> bytes:
    """Strip every picture inside a zip, and drop the zip's comments and extra fields."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(out, "w") as target:
        for member in source.infolist():
            content = source.read(member)
            strip = STRIPPERS.get(Path(member.filename).suffix.lower())
            if strip is not None and strip is not strip_zip:
                content = strip(content)
            clean = zipfile.ZipInfo(member.filename, member.date_time)
            clean.compress_type = member.compress_type
            target.writestr(clean, content)
    return out.getvalue()


STRIPPERS: dict[str, Callable[[bytes], bytes]] = {
    ".jpg": strip_jpeg,
    ".jpeg": strip_jpeg,
    ".jfif": strip_jpeg,
    ".png": strip_png,
    ".apng": strip_png,
    ".webp": strip_webp,
    ".gif": strip_gif,
    ".avif": strip_heif,
    ".heic": strip_heif,
    ".heif": strip_heif,
    ".jxl": strip_jxl,
    ".tif": strip_tiff,
    ".tiff": strip_tiff,
    ".zip": strip_zip,
}
# What a stripper raises for a file it cannot read as what its name says.
CANNOT = (ValueError, IndexError, OSError, zipfile.BadZipFile, Image.DecompressionBombError)


def strip_file(path: Path) -> bool:
    """Remove a picture's, or a zip of pictures', metadata in place, keeping its date.

    Byte for byte where the format allows (everything but TIFF, which is saved
    again losslessly and checked pixel by pixel). False if it could not be done.
    """
    strip = STRIPPERS.get(path.suffix.lower())
    if strip is None or not path.is_file():
        return False
    data = path.read_bytes()
    try:
        clean = strip(data)
    except CANNOT:
        return False
    if clean != data:
        when = path.stat()
        spare = path.with_name(path.name + ".bare")
        spare.write_bytes(clean)
        spare.replace(path)
        os.utime(path, ns=(when.st_atime_ns, when.st_mtime_ns))
    return True


# Subtitle codecs ffmpeg can turn into text; picture-based ones (PGS, DVD) cannot be.
TEXT_SUBTITLES = frozenset({"subrip", "mov_text", "webvtt", "ass", "ssa", "text"})
SRT_TIME = re.compile(r"(\d{2}:\d{2}:\d{2}),(\d{3})")


def as_webvtt(text: str) -> str:
    """Return subtitles as WebVTT, which the player reads; SRT differs only in its commas."""
    if text.lstrip("\ufeff").startswith("WEBVTT"):
        return text
    return "WEBVTT\n\n" + SRT_TIME.sub(r"\1.\2", text.replace("\r\n", "\n"))


def subtitle_tracks(path: Path) -> list[dict[str, str]]:
    """Return the subtitles a video has, beside it and inside it, each as WebVTT."""
    found: list[dict[str, str]] = []
    for side in sorted(path.parent.glob(glob.escape(path.stem) + ".*")):
        if side.suffix.lower() in {".vtt", ".srt"}:
            label = side.name[len(path.stem) : -len(side.suffix)].strip(".") or "Subtitles"
            text = side.read_text(encoding="utf-8", errors="replace")
            found.append({"label": label, "vtt": as_webvtt(text)})
    listing = [
        paths.tool("ffprobe"),
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=codec_name:stream_tags=language,title",
        "-of",
        "json",
        str(path),
    ]
    try:
        streams = store.items(
            store.record(json.loads(process.run(listing, timeout=30).stdout)).get("streams")
        )
    except ValueError:
        streams = []
    for number, stream in enumerate(streams):
        info = store.record(stream)
        if info.get("codec_name") not in TEXT_SUBTITLES:
            continue
        tags = store.record(info.get("tags"))
        label = str(tags.get("title") or tags.get("language") or f"Track {number + 1}")
        extract = [
            ffmpeg(),
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            f"0:s:{number}",
            "-f",
            "webvtt",
            "-",
        ]
        text = process.run(extract, timeout=120).stdout
        if text.strip():
            found.append({"label": label, "vtt": text})
    return found


def save_frame(path: Path, seconds: float) -> Path | None:
    """Save the frame at a moment as a lossless PNG beside the video, with no metadata."""
    whole = int(seconds)
    target = beside(path, f"frame {whole // 60}m{whole % 60:02d}s", ".png")
    command = [
        ffmpeg(),
        "-v",
        "error",
        "-ss",
        f"{seconds:.3f}",
        "-i",
        str(path),
        "-frames:v",
        "1",
        "-map_metadata",
        "-1",
        "-fflags",
        "+bitexact",
        "-flags:v",
        "+bitexact",
        "-y",
        str(target),
    ]
    done = process.run(command, timeout=60)
    if done.returncode == 0 and target.is_file() and target.stat().st_size:
        return target
    target.unlink(missing_ok=True)
    return None


def kept(path: Path, folder: Path, suffix: str) -> Path:
    """Return where a picture made from a file is kept.

    By the file's path, size and time, so an edited file gets a new one.
    """
    stat = path.stat()
    key = hashlib.sha256(f"{path}|{stat.st_size}|{stat.st_mtime_ns}".encode()).hexdigest()[:20]
    return folder / f"{key}{suffix}"


def waveform(path: Path, folder: Path) -> Path | None:
    """Return a picture of a file's sound as a hairline waveform, drawn once and kept."""
    target = kept(path, folder, ".png")
    if target.is_file():
        return target
    folder.mkdir(parents=True, exist_ok=True)
    draw = "aformat=channel_layouts=mono,showwavespic=s=1600x200:colors=0xecebe6:scale=sqrt"
    command = [ffmpeg(), "-v", "error", "-i", str(path), "-filter_complex", draw]
    command += ["-frames:v", "1", "-y", str(target)]
    with DRAWING:
        done = process.run(command, timeout=120)
    return target if done.returncode == 0 and target.is_file() else None


def thumbnail(path: Path, folder: Path, *, video: bool) -> Path | None:
    """Return a small square picture of a file for its library tile, made once and kept.

    A tile showing the file itself decodes a whole photo, or holds a video
    decoder open, for every tile on screen, which a slow computer cannot do.
    """
    target = kept(path, folder, ".jpg")
    if target.is_file():
        return target
    folder.mkdir(parents=True, exist_ok=True)
    with DRAWING:
        if video:
            return video_thumbnail(path, target)
        try:
            with Image.open(path) as image:
                image.draft("RGB", (THUMB, THUMB))  # a JPEG decodes at a fraction of its size
                square = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), (THUMB, THUMB))
                square.save(target, "JPEG", quality=85)
        except CANNOT:
            return None
    return target


def video_thumbnail(path: Path, target: Path) -> Path | None:
    """Make a video's tile from a frame a quarter in, as a film opens on black titles."""
    length = duration(path) or 0
    at = min(length / 4, 90) if length > VIDEO_INTRO else 0
    square = f"scale={THUMB}:{THUMB}:force_original_aspect_ratio=increase,crop={THUMB}:{THUMB}"
    command = [ffmpeg(), "-v", "error", "-ss", f"{at:.2f}", "-i", str(path), "-frames:v", "1"]
    command += ["-vf", square, "-q:v", "4", "-y", str(target)]
    done = process.run(command, timeout=60)
    return target if done.returncode == 0 and target.is_file() else None
