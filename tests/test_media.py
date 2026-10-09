"""Transcripts from subtitles, new files that never overwrite old ones, and bare files."""

import io
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from PIL import Image, ImageSequence, PngImagePlugin

from keepsake import media
from keepsake.media import (
    JXL_SIGNATURE,
    as_webvtt,
    audio_command,
    beside,
    save_frame,
    scrub_command,
    strip_file,
    subtitle_tracks,
    transcript,
    trim_command,
)

SOURCE = "https://source.example/watch?v=1"

ROLLING = """1
00:00:00,000 --> 00:00:02,000
<c>hello there</c>

2
00:00:02,000 --> 00:00:04,000
hello there

3
00:00:04,000 --> 00:00:06,000
general Kenobi. You are a bold one.
"""


def test_a_transcript_is_the_words_only_said_once() -> None:
    """Numbers, timings and tags go; a rolling caption's repeat is not said twice."""
    assert transcript(ROLLING) == "hello there general Kenobi. You are a bold one.\n"


def test_a_long_transcript_is_broken_into_paragraphs() -> None:
    """Five sentences to a paragraph, so it reads as prose."""
    words = "\n\n".join(f"{i}\n00:00:0{i},000 --> 00:00:0{i},500\nLine {i}." for i in range(7))
    assert transcript(words).count("\n\n") == 1


def test_a_converted_file_never_replaces_one_already_there(tmp_path: Path) -> None:
    """A second conversion gets a number."""
    source = tmp_path / "clip.mp4"
    first = beside(source, "gif", ".gif")
    assert first.name == "clip (gif).gif"
    first.write_bytes(b"")
    assert beside(source, "gif", ".gif").name == "clip (gif 2).gif"


def test_webvtt_captions_become_a_transcript_too() -> None:
    """The header, cue settings and inline timestamps are not words anybody said."""
    captions = (
        "WEBVTT\nKind: captions\nLanguage: en\n\n"
        "00:00.000 --> 00:02.000 align:start position:0%\n"
        "all<00:00:00.500><c> right</c>\n\n"
        "00:00:02.000 --> 00:00:04.000\nso here we are.\n"
    )
    assert transcript(captions) == "all right so here we are.\n"


def planted(tmp_path: Path, suffix: str) -> tuple[Path, bytes, bytes]:
    """Save a picture carrying a camera, a link and a colour profile; return its pixels too."""
    picture = Image.new("RGB", (16, 16), (200, 30, 90))
    exif = Image.Exif()
    exif[0x010F] = "SecretCamera"  # Make
    exif[0x010E] = SOURCE  # ImageDescription
    profile = b"colour profile bytes"  # carried, never read, so any bytes will do
    path = tmp_path / f"a{suffix}"
    if suffix == ".png":
        text = PngImagePlugin.PngInfo()
        text.add_text("Comment", SOURCE)
        picture.save(path, pnginfo=text, exif=exif, icc_profile=profile)
    elif suffix == ".webp":
        picture.save(path, exif=exif, xmp=SOURCE.encode(), icc_profile=profile, lossless=True)
    else:
        picture.save(path, exif=exif, comment=SOURCE, icc_profile=profile, quality=95)
    with Image.open(path) as saved:
        return path, saved.convert("RGB").tobytes(), profile


@pytest.mark.parametrize("suffix", [".jpg", ".png", ".webp"])
def test_a_picture_loses_its_metadata_but_not_a_pixel(tmp_path: Path, suffix: str) -> None:
    """Camera, link and text go, byte for byte; the pixels, colour profile and date stay."""
    path, pixels, profile = planted(tmp_path, suffix)
    assert b"SecretCamera" in path.read_bytes()
    assert SOURCE.encode() in path.read_bytes()
    stamp = 1_000_000_000 * 10**9  # an upload date, set as "File date" does
    os.utime(path, ns=(stamp, stamp))
    assert strip_file(path)
    data = path.read_bytes()
    assert b"SecretCamera" not in data
    assert SOURCE.encode() not in data
    assert path.stat().st_mtime_ns == stamp
    with Image.open(path) as bare:
        assert bare.convert("RGB").tobytes() == pixels
        assert bare.info.get("icc_profile") == profile
        assert not bare.getexif()


def frames(path: Path) -> list[bytes]:
    """Return every frame of a picture, decoded."""
    with Image.open(path) as picture:
        return [frame.convert("RGB").tobytes() for frame in ImageSequence.Iterator(picture)]


def test_a_gif_loses_its_comment_but_keeps_its_frames_and_loop(tmp_path: Path) -> None:
    """The comment block goes; the frames, their timing and the looping stay."""
    gif = tmp_path / "a.gif"
    red, blue = Image.new("RGB", (8, 8), (255, 0, 0)), Image.new("RGB", (8, 8), (0, 0, 255))
    red.save(gif, save_all=True, append_images=[blue], loop=0, duration=100, comment=SOURCE)
    before = frames(gif)
    assert SOURCE.encode() in gif.read_bytes()
    assert strip_file(gif)
    assert SOURCE.encode() not in gif.read_bytes()
    assert b"NETSCAPE2.0" in gif.read_bytes()
    assert frames(gif) == before


def test_an_avif_has_its_exif_and_xmp_zeroed_where_they_lie(tmp_path: Path) -> None:
    """In place, so no offset moves and the picture decodes exactly as before."""
    avif = tmp_path / "a.avif"
    exif = Image.Exif()
    exif[0x010F] = "SecretCamera"
    Image.new("RGB", (16, 16), (10, 120, 200)).save(avif, exif=exif, xmp=SOURCE.encode())
    before, size = frames(avif), avif.stat().st_size
    assert strip_file(avif)
    data = avif.read_bytes()
    assert b"SecretCamera" not in data
    assert SOURCE.encode() not in data
    assert len(data) == size
    assert frames(avif) == before


def box(kind: bytes, payload: bytes) -> bytes:
    """Return one ISO box."""
    return (8 + len(payload)).to_bytes(4, "big") + kind + payload


def test_a_jpeg_xl_keeps_its_picture_and_drops_its_metadata_boxes(tmp_path: Path) -> None:
    """Exif, XMP (plain or Brotli-wrapped) and JUMBF boxes go; the codestream stays."""
    picture = box(b"ftyp", b"jxl \0\0\0\0jxl ") + box(b"jxlc", b"the picture itself")
    extras = box(b"Exif", b"\0\0\0\0SecretCamera") + box(b"brob", b"xml compressed")
    jxl = tmp_path / "a.jxl"
    jxl.write_bytes(JXL_SIGNATURE + picture + extras + box(b"jumb", b"provenance"))
    assert strip_file(jxl)
    assert jxl.read_bytes() == JXL_SIGNATURE + picture


def test_a_tiff_is_saved_again_losslessly_without_its_tags(tmp_path: Path) -> None:
    """Artist and description go; every pixel is the same."""
    tiff = tmp_path / "a.tif"
    Image.new("RGB", (16, 16), (7, 77, 177)).save(tiff, tiffinfo={315: "SecretArtist", 270: SOURCE})
    before = frames(tiff)
    assert b"SecretArtist" in tiff.read_bytes()
    assert strip_file(tiff)
    assert b"SecretArtist" not in tiff.read_bytes()
    assert SOURCE.encode() not in tiff.read_bytes()
    assert frames(tiff) == before


def test_pictures_inside_a_zip_are_stripped_and_the_zip_comment_goes(tmp_path: Path) -> None:
    """A gallery zip is cleaned member by member; other files in it are untouched."""
    jpeg = io.BytesIO()
    exif = Image.Exif()
    exif[0x010F] = "SecretCamera"
    Image.new("RGB", (8, 8)).save(jpeg, "JPEG", exif=exif)
    archive = tmp_path / "gallery.zip"
    with zipfile.ZipFile(archive, "w") as made:
        made.comment = SOURCE.encode()
        made.writestr("1.jpg", jpeg.getvalue())
        made.writestr("notes.txt", "kept as it is")
    assert strip_file(archive)
    with zipfile.ZipFile(archive) as cleaned:
        assert b"SecretCamera" not in cleaned.read("1.jpg")
        assert cleaned.read("notes.txt") == b"kept as it is"
        assert not cleaned.comment


def test_a_kind_of_file_it_cannot_strip_is_left_alone(tmp_path: Path) -> None:
    """A BMP carries nothing to strip, and is not rewritten."""
    bmp = tmp_path / "a.bmp"
    Image.new("RGB", (4, 4)).save(bmp)
    before = bmp.read_bytes()
    assert not strip_file(bmp)
    assert bmp.read_bytes() == before


FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")


@pytest.mark.skipif(not (FFMPEG and FFPROBE), reason="needs ffmpeg")
@pytest.mark.parametrize("suffix", [".mp4", ".mp3"])
def test_a_video_or_song_keeps_only_picture_and_sound(tmp_path: Path, suffix: str) -> None:
    """Tags, the link, chapters and cover art all stay behind."""
    assert FFMPEG
    assert FFPROBE
    chapters = tmp_path / "chapters.txt"
    chapters.write_text(";FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1\nSTART=0\nEND=1\ntitle=Intro\n")
    cover = tmp_path / "cover.png"
    Image.new("RGB", (16, 16)).save(cover)
    source, bare = tmp_path / f"in{suffix}", tmp_path / f"out{suffix}"
    picture = ["-f", "lavfi", "-i", "color=blue:s=64x64:d=1"] if suffix == ".mp4" else []
    streams = (
        ["-map", "3:v", "-map", "2:a", "-map", "1:v"]
        if suffix == ".mp4"
        else ["-map", "2:a", "-map", "1:v"]
    )
    codecs = ["-c:v:0", "libx264", "-c:a", "aac"] if suffix == ".mp4" else ["-c:a", "libmp3lame"]
    cover_codec = "-c:v:1" if suffix == ".mp4" else "-c:v"
    make = [
        FFMPEG,
        "-v",
        "error",
        "-i",
        str(chapters),
        "-i",
        str(cover),
        "-f",
        "lavfi",
        "-i",
        "sine=d=1",
        *picture,
        *streams,
        *codecs,
        cover_codec,
        "png",
        "-disposition:v:1" if suffix == ".mp4" else "-disposition:v",
        "attached_pic",
        "-map_chapters",
        "0",
        "-metadata",
        "title=Secret",
        "-metadata",
        f"purl={SOURCE}",
        "-metadata",
        f"comment={SOURCE}",
        str(source),
    ]
    subprocess.run(make, check=True, capture_output=True)
    subprocess.run(scrub_command(source, bare), check=True, capture_output=True)
    probe = [
        FFPROBE,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        "-of",
        "json",
        str(bare),
    ]
    found = json.loads(subprocess.run(probe, check=True, capture_output=True, text=True).stdout)
    assert found["chapters"] == []
    kinds = sorted(stream["codec_type"] for stream in found["streams"])
    assert kinds == (["audio", "video"] if suffix == ".mp4" else ["audio"])
    assert not any(stream["disposition"].get("attached_pic") for stream in found["streams"])
    words = json.dumps(
        [found["format"].get("tags", {}), *(s.get("tags", {}) for s in found["streams"])]
    )
    assert "Secret" not in words
    assert "source.example" not in words


def test_subtitles_beside_a_video_reach_the_player_as_webvtt(tmp_path: Path) -> None:
    """SRT differs from WebVTT in its header and its commas; the label is the language part."""
    srt = "1\r\n00:00:01,500 --> 00:00:03,000\r\nHello\r\n"
    assert as_webvtt(srt) == "WEBVTT\n\n1\n00:00:01.500 --> 00:00:03.000\nHello\n"
    assert as_webvtt("WEBVTT\n\nx") == "WEBVTT\n\nx"
    video = tmp_path / "Talk [x].mp4"
    video.write_bytes(b"not really a video")
    (tmp_path / "Talk [x].en.srt").write_text(srt, encoding="utf-8")
    (tmp_path / "Other.en.srt").write_text(srt, encoding="utf-8")
    tracks = subtitle_tracks(video)
    assert [track["label"] for track in tracks] == ["en"]
    assert tracks[0]["vtt"].startswith("WEBVTT")


@pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg")
def test_a_frame_is_saved_beside_the_video_as_a_picture(tmp_path: Path) -> None:
    """The moment is in the name, and it is the video's own size."""
    assert FFMPEG
    video = tmp_path / "Talk.mp4"
    make = [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=160x90:d=3", str(video)]
    subprocess.run(make, check=True, capture_output=True)
    saved = save_frame(video, 1.5)
    assert saved is not None
    assert saved.name == "Talk (frame 0m01s).png"
    with Image.open(saved) as picture:
        assert picture.size == (160, 90)


@pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg")
def test_a_waveform_is_drawn_once_and_again_when_the_file_changes(tmp_path: Path) -> None:
    """The second ask for the same file gets the kept picture; an edited file gets a new one."""
    assert FFMPEG
    song = tmp_path / "Song.flac"
    make = [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "sine=d=2", str(song)]
    subprocess.run(make, check=True, capture_output=True)
    first = media.waveform(song, tmp_path / "waves")
    assert first is not None
    assert media.waveform(song, tmp_path / "waves") == first
    with Image.open(first) as picture:
        assert picture.size == (1600, 200)
    subprocess.run([*make[:-1], "-y", str(song)], check=True, capture_output=True)
    os.utime(song, ns=(1, 1))
    assert media.waveform(song, tmp_path / "waves") not in (None, first)


def test_a_tile_gets_a_small_square_of_a_picture_turned_the_way_it_shows(tmp_path: Path) -> None:
    """A wide photo becomes a square crop of its middle, upright as its EXIF says, made once."""
    photo = tmp_path / "Wide.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # stored on its side: shown turned a quarter clockwise
    stored = Image.new("RGB", (2400, 1200), "blue")
    stored.paste("red", (0, 0, 1200, 1200))  # the stored left half, which shows as the top
    stored.save(photo, exif=exif)
    first = media.thumbnail(photo, tmp_path / "thumbs", video=False)
    assert first is not None
    with Image.open(first) as tile:
        assert tile.size == (media.THUMB, media.THUMB)
        top, bottom = tile.getpixel((176, 20)), tile.getpixel((176, 330))
    assert isinstance(top, tuple)
    assert isinstance(bottom, tuple)
    assert top[0] > 200 > top[2]
    assert bottom[2] > 200 > bottom[0]
    first.write_bytes(b"kept")
    assert media.thumbnail(photo, tmp_path / "thumbs", video=False) == first
    assert first.read_bytes() == b"kept"
    broken = tmp_path / "Broken.jpg"
    broken.write_bytes(b"not a picture")
    assert media.thumbnail(broken, tmp_path / "thumbs", video=False) is None


@pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg")
def test_a_video_tile_is_a_frame_from_inside_it(tmp_path: Path) -> None:
    """A video gets the same square, from a frame rather than a decoder held open per tile."""
    assert FFMPEG
    video = tmp_path / "Talk.mp4"
    make = [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x180:d=12", str(video)]
    subprocess.run(make, check=True, capture_output=True)
    made = media.thumbnail(video, tmp_path / "thumbs", video=True)
    assert made is not None
    with Image.open(made) as tile:
        assert tile.size == (media.THUMB, media.THUMB)


def test_sound_already_in_the_format_is_copied_not_encoded(monkeypatch: pytest.MonkeyPatch) -> None:
    """AAC goes into an M4A as it is, and only a different format or a cut's lead-in re-encodes."""

    def codecs(_: Path) -> tuple[str, str]:
        return "h264", "aac"

    def from_zero(_: Path) -> bool:
        return False

    monkeypatch.setattr(media, "codecs", codecs)
    monkeypatch.setattr(media, "lead_in", from_zero)
    copied = audio_command(Path("a.mp4"), Path("a.M4A"))
    assert copied[copied.index("-c:a") + 1] == "copy"
    encoded = audio_command(Path("a.mp4"), Path("a.flac"))
    assert encoded[encoded.index("-c:a") + 1 :][:2] == ["flac", "-progress"]

    def before_zero(_: Path) -> bool:
        return True

    monkeypatch.setattr(media, "lead_in", before_zero)
    cut = audio_command(Path("a.mp4"), Path("a.m4a"))
    assert cut[cut.index("-c:a") + 1] == "aac"
    part = audio_command(Path("a.mp4"), Path("a.m4a"), 3, 8)
    assert part[part.index("-i") + 2 : part.index("-i") + 6] == ["-ss", "3.000", "-to", "8.000"]


def test_flac_is_always_encoded_so_its_header_has_the_clip_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A copied FLAC keeps the source's sample count, and encoding FLAC loses nothing."""

    def codecs(_: Path) -> tuple[str, str]:
        return "", "flac"

    def from_zero(_: Path) -> bool:
        return False

    monkeypatch.setattr(media, "codecs", codecs)
    monkeypatch.setattr(media, "lead_in", from_zero)
    saved = audio_command(Path("a.flac"), Path("a (clip).flac"), 3, 8)
    assert saved[saved.index("-c:a") + 1] == "flac"
    cut = trim_command(Path("a.flac"), Path("a (clip).flac"), 3, 8, exact=False)
    assert cut[cut.index("-c:a") + 1] == "flac"
    assert "copy" not in cut
