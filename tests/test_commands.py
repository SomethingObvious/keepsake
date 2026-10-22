"""The command lines: each option becomes exactly the flags it should, and nothing breaks them."""

import json
from pathlib import Path

from keepsake import commands
from keepsake.commands import (
    gallery_command,
    match_filters,
    range_size,
    seconds,
    split_args,
    stage_name,
    video_sort,
    ytdlp_command,
    ytdlp_date,
)
from keepsake.jobs import Job, YtDlpReader
from keepsake.options import Options


def after(command: list[str], flag: str) -> str:
    """Return the value that follows a flag in a command line."""
    return command[command.index(flag) + 1]


def test_resolution_always_comes_before_codec() -> None:
    """Pinning a codec first once halved every photograph afterimage made from a reel."""
    options = Options(quality="1080", codec="av1")
    assert video_sort(options) == "res:1080,vcodec:av01,hdr:sdr,ext:mp4:m4a"
    assert video_sort(Options(codec="any", prefer_sdr=False, container="mkv")) == "res"


def test_plays_everywhere_ranks_h264_above_resolution() -> None:
    """When the point is a file that plays, H.264 wins even over pixels."""
    assert video_sort(Options(always_plays=True)).startswith("vcodec:h264,res")


def test_audio_is_extracted_with_cover_art_that_fits() -> None:
    """MP3 gets cover art; WAV cannot hold it and would fail the whole download."""
    audio = ytdlp_command(Options(mode="audio", strip_metadata=False), "https://x/y", None)
    assert "-x" in audio
    assert after(audio, "--audio-format") == "mp3"
    assert "--embed-thumbnail" in audio
    assert "--embed-subs" not in audio
    wav = ytdlp_command(Options(mode="audio", audio_format="wav"), "https://x/y", None)
    assert "--embed-thumbnail" not in wav
    webm = ytdlp_command(Options(container="webm"), "https://x/y", None)
    assert "--embed-thumbnail" not in webm


def test_music_mode_tags_an_album_and_squares_the_cover() -> None:
    """Artist from the uploader, album from the playlist, track number from its place."""
    command = ytdlp_command(
        Options(mode="audio", music=True, strip_metadata=False), "https://x/y", None
    )
    assert "%(album,playlist_title|)s:%(meta_album)s" in command
    assert commands.SQUARE in command


def test_removing_metadata_embeds_and_writes_nothing_about_the_file() -> None:
    """On by default, it overrides every switch that would describe the file."""
    described = Options(mode="audio", music=True, write_info_json=True, write_description=True)
    command = ytdlp_command(described, "https://x/y", None)
    for flag in ("--embed-thumbnail", "--embed-metadata", "--embed-chapters", "--write-info-json"):
        assert flag not in command
    assert "--write-description" not in command
    assert commands.SQUARE not in command
    assert "%(album,playlist_title|)s:%(meta_album)s" not in command
    assert "--write-metadata" not in gallery_command(
        Options(write_metadata=True), "https://x/y", None
    )
    kept = ytdlp_command(described.but({"strip_metadata": False}), "https://x/y", None)
    assert "--embed-metadata" in kept
    assert "--write-info-json" in kept


def test_best_quality_never_re_encodes_anything() -> None:
    """No plays-everywhere pass, no precise cuts, lossless covers and Pixiv animations."""
    asked = Options(quality="best", always_plays=True, precise_cuts=True, section="1:00-2:00")
    command = ytdlp_command(asked, "https://x/y", None)
    assert "--force-keyframes-at-cuts" not in command
    assert after(command, "-S").startswith("res,")  # resolution before any codec
    assert "ext:mp4:m4a" not in after(command, "-S")
    covers = Options(quality="best", strip_metadata=False, container="mp4")
    assert after(ytdlp_command(covers, "https://x/y", None), "--convert-thumbnails") == "png"
    assert after(gallery_command(Options(), "https://x/y", None), "--ugoira") == "copy"
    webm = Options(ugoira="webm")
    assert after(gallery_command(webm, "https://x/y", None), "--ugoira") == "copy"
    smaller = Options(quality="720", ugoira="webm", strip_metadata=False, container="mp4")
    assert after(gallery_command(smaller, "https://x/y", None), "--ugoira") == "webm"
    assert after(ytdlp_command(smaller, "https://x/y", None), "--convert-thumbnails") == "jpg"
    assert "ext:mp4:m4a" in after(ytdlp_command(smaller, "https://x/y", None), "-S")


def test_each_kind_goes_to_its_own_folder_and_a_gallery_one_level_down() -> None:
    """Videos, music, pictures and transcripts apart; an empty one means with the videos."""
    o = Options(folder="V", audio_folder="M", picture_folder="P", text_folder="D")
    assert commands.folder_for(o) == "V"
    assert commands.folder_for(o.but({"mode": "audio"})) == "M"
    assert commands.folder_for(o.but({"mode": "images"})) == "P"
    assert commands.folder_for(o.but({"mode": "transcript"})) == "D"
    assert commands.folder_for(o, gallery=True) == "P"
    assert commands.folder_for(o.but({"mode": "audio", "audio_folder": ""})) == "V"
    link = "https://www.instagram.com/natgeo/"
    assert after(gallery_command(o, link, None), "-D") == str(Path("P") / "instagram natgeo")
    assert after(gallery_command(o.but({"by_site": True}), link, None), "-d") == "P"
    assert after(ytdlp_command(o, link, None), "-o") == o.template


def test_the_thumbnail_type_saves_only_the_best_thumbnail_as_a_jpeg_with_the_pictures(
    tmp_path: Path,
) -> None:
    """Nothing else is downloaded or written beside it, and the JPEG is what the job keeps."""
    o = Options(mode="thumbnail", picture_folder="P", subs="embed", write_description=True)
    command = ytdlp_command(o.but({"archive": True}), "https://youtu.be/x", None)
    assert after(command, "-P") == "P"
    assert after(command, "-o") == o.template
    assert after(command, "--convert-thumbnails") == "jpg"
    for flag in ("--skip-download", "--write-thumbnail", "--no-download-archive"):
        assert flag in command
    for flag in ("--write-subs", "--embed-subs", "--write-description", "--download-archive"):
        assert flag not in command
    assert "after_video:" + commands.WROTE in command
    picture = tmp_path / "Title [x].jpg"
    picture.write_bytes(b"")
    job = Job(url="https://youtu.be/x", mode="thumbnail", options=o)
    written = {
        "filepath": None,
        "filename": str(tmp_path / "Title [x].NA"),
        "thumbnails": [{"id": "0"}, {"filepath": str(tmp_path / "working" / picture.name)}],
    }
    YtDlpReader(job)("KEEPSAKE-FILE " + json.dumps(written))
    assert job.files == [str(picture)]


def test_the_url_always_comes_last_after_a_separator() -> None:
    """A link starting with a dash can never be read as an option."""
    command = ytdlp_command(Options(), "-oops", ("browser", "firefox"))
    assert command[-2:] == ["--", "-oops"]
    assert after(command, "--cookies-from-browser") == "firefox"


def test_filters_become_one_match_expression() -> None:
    """Shorts, members-only videos, lengths and titles, joined with &."""
    options = Options(
        skip_shorts=True,
        skip_members=True,
        min_duration="1:30",
        title_skip="trailer & tease",
    )
    rules = match_filters(options)
    assert "original_url!*=/shorts/" in rules
    assert "availability!=subscriber_only" in rules
    assert "duration>=90" in rules
    assert "title!~='(?i)trailer \\& tease'" in rules


def test_durations_and_dates_are_read_the_way_people_type_them() -> None:
    """90, 1:30 and 1:02:03 are durations; 2026-09-01 and now-7days are dates."""
    assert seconds("90") == 90
    assert seconds("1:02:03") == 3723
    assert seconds("soon") is None
    assert ytdlp_date("2026-09-01") == "20260901"
    assert ytdlp_date("now-7days") == "now-7days"
    assert ytdlp_date("next tuesday") is None


def test_chapters_picked_in_the_preview_match_exactly() -> None:
    """A chapter title with regex characters in it is matched literally."""
    command = ytdlp_command(Options(chapters="Intro (live)\nOutro"), "https://x/y", None)
    assert "^Intro\\ \\(live\\)$" in command
    assert "^Outro$" in command


def test_a_live_recording_is_never_overwritten_by_the_next() -> None:
    """Two recordings of one stream get different names."""
    command = ytdlp_command(Options(live_from_start=True), "https://x/y", None)
    assert "--live-from-start" in command
    assert "%(epoch)s" in after(command, "-o")


def test_a_renamed_download_carries_its_name_into_the_tags() -> None:
    """The name typed in the preview replaces the title, backslashes and all."""
    command = ytdlp_command(Options(rename="My \\ clip"), "https://x/y", None)
    at = command.index("--replace-in-metadata")
    assert command[at + 1 : at + 4] == ["title", ".+", "My \\\\ clip"]


def test_download_it_again_ignores_the_archive(data: Path) -> None:
    """The archive is skipped, and an existing file is replaced."""
    remembering = ytdlp_command(Options(archive=True), "https://x/y", None)
    assert after(remembering, "--download-archive") == str(data / "yt-dlp-archive.txt")
    again = ytdlp_command(Options(archive=True, ignore_archive=True), "https://x/y", None)
    assert "--no-download-archive" in again
    assert "--force-overwrites" in again


def test_a_careful_pace_slows_both_tools() -> None:
    """Careful waits between requests; off never waits at all."""
    careful = Options(politeness="careful")
    assert "--sleep-interval" in ytdlp_command(careful, "https://x/y", None)
    assert "--sleep-429" in gallery_command(careful, "https://x/y", None)
    assert "--sleep-requests" not in ytdlp_command(Options(politeness="off"), "https://x/y", None)


def test_a_gallery_command_reads_its_options() -> None:
    """Range, cookies, archive, and the upload date as the file date."""
    command = gallery_command(
        Options(range="1-24", file_date="upload"),
        "https://x/y",
        ("file", "c.txt"),
        archive=Path("a.sqlite3"),
    )
    assert after(command, "--range") == "1-24"
    assert after(command, "--cookies") == "c.txt"
    assert after(command, "--download-archive") == "a.sqlite3"
    assert after(command, "--mtime") == "date"
    assert command[-1] == "https://x/y"


def test_a_windows_path_survives_the_extra_arguments_box() -> None:
    """Backslashes are not escapes to anyone typing a path."""
    assert split_args(r'--cookies "C:\My Files\c.txt" -v') == [
        "--cookies",
        r"C:\My Files\c.txt",
        "-v",
    ]


def test_small_readers() -> None:
    """A gallery range's size, and a post-processing step's plain name."""
    assert range_size("1-24") == 24
    assert range_size("5-") is None
    assert stage_name("FFmpegMerger") == "Merging video and audio"
    assert stage_name("FFmpegFixupM3u8") == "Fixing up the file"
    assert stage_name("SomethingNew") == "Something new"
