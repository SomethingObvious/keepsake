"""Reading each tool's output into a job's progress."""

import json
from pathlib import Path

import pytest

from keepsake import jobs
from keepsake.jobs import GalleryReader, Job, YtDlpReader, finish, working_folder
from keepsake.options import Options


def make(**changes: object) -> Job:
    """Return a job for a made-up link."""
    return Job(url="https://example.com/v", mode="video", options=Options().but(changes))


def test_progress_lines_become_a_percentage_speed_and_time_left() -> None:
    """Bytes so far over the total, falling back to the estimate."""
    job = make()
    reader = YtDlpReader(job)
    reader("KEEPSAKE-PROG 500 1000 NA 250000.5 12")
    assert job.pct == 50.0
    assert job.speed == 250000.5
    assert job.eta == 12.0
    reader("KEEPSAKE-PROG 10 NA 100 NA NA")
    assert job.pct == 10.0
    assert job.speed is None


def test_what_is_being_downloaded_is_read_from_its_json() -> None:
    """Title, playlist, thumbnail and site; a script URL is never kept as a thumbnail."""
    job = make()
    reader = YtDlpReader(job)
    info = {
        "id": "abc",
        "title": "Item",
        "playlist_title": "Mix",
        "playlist_index": 2,
        "playlist_count": 9,
        "thumbnail": "javascript:alert(1)",
        "webpage_url": "https://www.youtube.com/watch?v=abc",
    }
    reader("KEEPSAKE-META " + json.dumps(info))
    assert job.title == "Mix"
    assert job.item == "Item"
    assert job.index == 2
    assert job.count == 9
    assert job.thumb == ""
    assert job.ids == ["abc"]
    assert job.site == "youtube.com"


def test_a_finished_file_takes_the_upload_date_when_asked(tmp_path: Path) -> None:
    """The file's modified time becomes the upload time."""
    video = tmp_path / "v.mp4"
    video.write_bytes(b"")
    job = make(file_date="upload")
    YtDlpReader(job)(
        "KEEPSAKE-FILE " + json.dumps({"filepath": str(video), "timestamp": 1_000_000})
    )
    assert job.files == [str(video)]
    assert int(video.stat().st_mtime) == 1_000_000


def test_errors_are_kept_for_the_advice() -> None:
    """The last ERROR line is what the user is told about."""
    job = make()
    reader = YtDlpReader(job)
    reader("ERROR: first")
    reader("ERROR: [youtube] x: Video unavailable")
    assert reader.last_error == "ERROR: [youtube] x: Video unavailable"
    assert job.errors == 2
    assert list(job.log)[-1] == "ERROR: [youtube] x: Video unavailable"


def test_gallery_dl_is_read_from_the_paths_it_prints(tmp_path: Path) -> None:
    """A skipped file still belongs to the gallery; its folder names the title."""
    picture = tmp_path / "instagram" / "someone" / "1.jpg"
    picture.parent.mkdir(parents=True)
    picture.write_bytes(b"")
    job = make(folder=str(tmp_path))
    reader = GalleryReader(job, limit=4)
    reader(f"# {picture}")
    reader("[instagram][error] HttpError: 500")
    assert job.files == [str(picture)]
    assert job.pct == 25.0
    assert job.site == "example.com"
    assert job.title == "someone"
    assert job.thumb.startswith("file:///")
    assert reader.last_error.endswith("500")


def test_a_run_is_judged_by_what_it_wrote() -> None:
    """Nothing written is a failure; something written despite errors is a success."""
    job = make()
    assert finish(job, 0, "", "yt-dlp") == (False, "ERROR: nothing was written")
    job.files = ["somewhere"]
    assert finish(job, 1, "ERROR: one private video", "yt-dlp") == (True, "")
    assert finish(make(), 2, "", "gallery-dl") == (
        False,
        "ERROR: gallery-dl stopped with exit code 2",
    )


def test_a_job_restored_after_a_restart_is_the_same_job() -> None:
    """Everything needed to start again comes back."""
    job = make(quality="720")
    job.sub, job.archive, job.ytdlp_extra = "sub1", "C:/a", ["--break-on-existing"]
    again = Job.restore(job.saved())
    assert again is not None
    assert (again.url, again.sub, again.archive) == (job.url, "sub1", "C:/a")
    assert again.ytdlp_extra == ["--break-on-existing"]
    assert again.options.quality == "720"
    assert Job.restore({"mode": "video"}) is None


def test_a_check_that_stops_at_a_known_video_found_nothing_new() -> None:
    """Stopping at a filter or the archive is success with no files, not a failure."""
    job = make()
    reader = YtDlpReader(job)
    reader("[download] Talk does not pass filter (upload_date>=20260924), skipping ..")
    assert job.skipped
    assert finish(job, 101, "", "yt-dlp") == (True, "")


def test_two_downloads_of_one_video_never_share_a_working_folder() -> None:
    """Even of one link in one mode (MP3 and FLAC, say); a restarted job keeps its own."""
    first, second = make(), make()
    assert working_folder(first) != working_folder(second)
    again = Job.restore(first.saved())
    assert again is not None
    assert working_folder(again) == working_folder(first)


def test_the_files_written_beside_a_video_are_the_jobs_too(tmp_path: Path) -> None:
    """Chapters where they were cut; thumbnails and subtitles moved beside the video."""
    video = tmp_path / "T [abc].mp4"
    chapter = tmp_path / "T - 001 Intro [abc].mp4"
    thumb, subs = tmp_path / "T [abc].webp", tmp_path / "T [abc].en.vtt"
    for path in (video, chapter, thumb, subs):
        path.write_bytes(b"")
    before_the_move = "C:/working/Youtube/"
    info = {
        "filepath": str(video),
        "chapters": [{"title": "Intro", "filepath": str(chapter)}, {"title": "no file"}],
        "thumbnails": [{"url": "x"}, {"url": "y", "filepath": before_the_move + thumb.name}],
        "requested_subtitles": {"en": {"ext": "vtt", "filepath": before_the_move + subs.name}},
    }
    job = make()
    YtDlpReader(job)("KEEPSAKE-FILE " + json.dumps(info))
    assert sorted(job.files) == sorted(str(path) for path in (video, chapter, thumb, subs))


def test_a_download_keeps_its_unfinished_files_in_its_own_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """yt-dlp is told to work in the job's own folder."""
    seen: list[list[str]] = []

    def pretend(_job: Job, command: list[str], _reader: object) -> int:
        seen.append(command)
        return 0

    monkeypatch.setattr(jobs, "execute", pretend)
    job = make()
    jobs.run_ytdlp(job, None)
    assert f"temp:{working_folder(job)}" in seen[0]


def test_ffmpeg_progress_becomes_a_percentage_and_time_left() -> None:
    """Its speed, as so many times faster than playing, is turned into the time it has left."""
    job = make()
    reader = jobs.FfmpegReader(job, 600)
    reader("out_time_us=150000000")
    reader("speed=N/A")
    assert job.pct == 25.0
    assert job.eta is None
    reader("speed=100x")
    assert job.eta == 4.5
