"""The queue's clock, order and memory, without running a single download."""

import csv
import os
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import pytest

from keepsake import textremoval
from keepsake.downloads import History, Queue, clock, drop_ids, find_zips, next_time, within
from keepsake.jobs import Job, Outcome
from keepsake.options import Options


@pytest.fixture
def queue() -> Queue:
    """Return a queue that is paused, so adding a job never starts a real download."""
    made = Queue(Options, lambda _job: None, lambda: None)
    made.hold(held=True)
    return made


def test_times_of_day_are_read_the_way_people_type_them() -> None:
    """1:00 and 01:00 are the same; 25:00 is not a time."""
    assert clock("1:00") == (1, 0)
    assert clock("23:59") == (23, 59)
    assert clock("25:00") is None
    assert clock("soon") is None


def test_a_download_window_can_run_past_midnight() -> None:
    """01:00 to 07:00 is the night; 22:00 to 06:00 wraps round."""
    at = datetime(2026, 9, 24, 3, 30).astimezone()
    assert within(at, (1, 0), (7, 0))
    assert within(at, (22, 0), (6, 0))
    assert not within(at, (9, 0), (17, 0))


def test_a_scheduled_start_is_the_next_time_the_clock_shows_it() -> None:
    """02:00 asked for at 03:00 means tomorrow."""
    now = datetime(2026, 9, 24, 3, 0).astimezone()
    assert next_time((2, 0), now).day == 25
    assert next_time((4, 0), now).day == 24


def test_a_paused_queue_says_why_nothing_starts(queue: Queue) -> None:
    """The reason is shown above the queue."""
    job = queue.add("https://example.com/a", "video", Options())
    assert job.status == "queued"
    assert queue.reason == "Queue paused"


def test_waiting_jobs_can_be_moved(queue: Queue) -> None:
    """Top, up, down and bottom reorder what runs next."""
    ids = [queue.add(f"https://example.com/{n}", "video", Options()).id for n in range(4)]
    queue.move(ids[3], "top")
    assert list(queue.jobs) == [ids[3], ids[0], ids[1], ids[2]]
    queue.move(ids[3], "down")
    assert list(queue.jobs) == [ids[0], ids[3], ids[1], ids[2]]
    queue.move(ids[0], "bottom")
    assert list(queue.jobs) == [ids[3], ids[1], ids[2], ids[0]]


def test_a_flaky_failure_is_retried_later_and_a_refusal_can_be_repaired(queue: Queue) -> None:
    """A rate limit waits 30 seconds; a 403 is marked for Repair."""
    flaky = Job(url="https://x/1", mode="video", options=Options())
    queue.settle(flaky, ok=False, message="ERROR: HTTP Error 429: Too Many Requests")
    assert flaky.status == "queued"
    assert flaky.retry_at > time.time() + 20
    refused = Job(url="https://x/2", mode="video", options=Options(), tool="yt-dlp")
    queue.settle(refused, ok=False, message="ERROR: [youtube] a: HTTP Error 403: Forbidden")
    assert refused.status == "failed"
    assert refused.repairable
    assert "turned the request away" in refused.advice


def test_a_stopped_job_is_paused_or_cancelled_not_failed(queue: Queue) -> None:
    """Pausing is not a failure, and is not written to the history."""
    job = Job(url="https://x/1", mode="video", options=Options(), stop="pause")
    queue.settle(job, ok=False, message="ERROR: whatever")
    assert job.status == "paused"
    assert queue.history.entries == []


def test_retry_failed_takes_jobs_that_only_half_worked(queue: Queue) -> None:
    """What arrived is done, the site's words are kept, and Retry Failed takes it too."""
    job = queue.add("https://x/list", "video", Options())
    job.files, job.errors = ["a.mp4"], 1
    job.log.append("ERROR: [youtube] b: Private video. Sign in if you've been granted access")
    queue.settle(job, ok=True, message="")
    assert (job.status, job.said) == ("done", "Private video.")
    assert queue.incomplete() == [job.id]
    assert queue.history.entries[0]["errors"] == 1


def test_the_queue_survives_a_restart(data: Path, queue: Queue) -> None:
    """Waiting and paused jobs come back; finished ones do not."""
    queue.add("https://example.com/wait", "audio", Options(quality="720"))
    queue.save()
    assert (data / "queue.json").is_file()
    again = Queue(Options, lambda _job: None, lambda: None)
    restored = next(iter(again.jobs.values()))
    assert restored.url == "https://example.com/wait"
    assert restored.mode == "audio"
    assert restored.options.quality == "720"


def test_history_remembers_counts_and_exports(data: Path, tmp_path: Path) -> None:
    """Totals by site, a downloaded-before lookup, and a spreadsheet."""
    history = History(data / "history.json")
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x" * 10)
    done = Job(url="https://yt/1", mode="video", options=Options(), status="done", site="Youtube")
    done.files = [str(video)]
    done.finished = time.time()
    history.remember(done)
    stats = history.stats()
    assert stats["done"] == 1
    assert stats["bytes"] == 10
    assert history.downloaded_before("https://yt/1") is not None
    sheet = tmp_path / "history.csv"
    history.export(sheet)
    with sheet.open(encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][:3] == ["finished", "status", "title"]
    assert rows[1][3] == "https://yt/1"


def test_catalogue_numbers_continue_after_the_history_and_a_restart(data: Path) -> None:
    """Numbers start after the history, survive a restart and carry on from the highest."""
    history = History(data / "history.json")
    for n in range(3):
        history.remember(Job(url=f"https://x/{n}", mode="video", options=Options(), status="done"))
    first = Queue(Options, lambda _job: None, lambda: None)
    first.hold(held=True)
    assert [first.add(f"https://y/{n}", "video", Options()).serial for n in range(2)] == [4, 5]
    first.save()
    again = Queue(Options, lambda _job: None, lambda: None)
    again.hold(held=True)
    assert sorted(job.serial for job in again.jobs.values()) == [4, 5]
    assert again.add("https://y/next", "video", Options()).serial == 6


def test_a_file_on_disk_finds_its_catalogue_number(data: Path) -> None:
    """The library looks files up by path, whatever case Windows was given it in."""
    history = History(data / "history.json")
    done = Job(url="https://x/1", mode="video", options=Options(), status="done", serial=7)
    done.files = [r"C:\Videos\Keepsake\Clip.mp4"]
    history.remember(done)
    assert history.serials() == {os.path.normcase(r"C:\Videos\Keepsake\Clip.mp4"): 7}
    assert history.serials()[os.path.normcase(r"c:\videos\keepsake\clip.MP4")] == 7


def test_a_skip_names_the_download_it_repeats_and_stays_out_of_history(queue: Queue) -> None:
    """The archive's skip carries only an id, so the title and date come from the history."""
    first = Job(url="https://yt/watch?v=abc", mode="video", options=Options(), status="done")
    first.title, first.keys, first.finished = "Real title", ["youtube abc"], 1_790_000_000.0
    queue.history.remember(first)
    again = Job(url="https://youtu.be/abc", mode="video", options=Options(), skipped=True)
    again.log.append("[download] abc: has already been recorded in the archive")
    queue.settle(again, ok=True, message="")
    assert again.title == "Real title"
    assert again.stage == "Already downloaded"
    assert again.repeat == 1_790_000_000.0
    assert len(queue.history.entries) == 1


def test_a_deleted_file_is_found_by_its_archive_line(data: Path) -> None:
    """Deleting a download has to know which archive line to forget."""
    history = History(data / "history.json")
    done = Job(url="https://x/1", mode="video", options=Options(), status="done")
    done.files, done.keys = [r"C:\V\a.mp4"], ["youtube abc"]
    history.remember(done)
    assert history.keys_for(Path(r"c:\v\A.MP4")) == ["youtube abc"]
    assert history.keys_for(Path(r"C:\V\b.mp4")) == []


def test_the_same_download_added_twice_is_one_job(queue: Queue) -> None:
    """A double click or a pasted repeat; the same link as another format is its own job."""
    mp3 = queue.add("https://example.com/song", "audio", Options(audio_format="mp3"))
    assert queue.add("https://example.com/song", "audio", Options(audio_format="mp3")) is mp3
    flac = queue.add("https://example.com/song", "audio", Options(audio_format="flac"))
    assert flac is not mp3
    assert len(queue.jobs) == 2


def test_a_video_id_leaves_the_file_names_and_a_clash_gets_one_number(tmp_path: Path) -> None:
    """The video and its subtitles are numbered together, so a player still pairs them."""
    (tmp_path / "Talk.mp4").write_bytes(b"another talk")
    names = ["Talk [abc123].mp4", "Talk [abc123].en.vtt", "[abc123].jpg", "Other [zzz].mp4"]
    for name in names:
        (tmp_path / name).write_bytes(b"")
    job = Job(url="https://example.com/v", mode="video", options=Options())
    job.files = [str(tmp_path / name) for name in names]
    job.ids = ["abc123", "abc123"]
    drop_ids(job)
    assert sorted(Path(name).name for name in job.files) == [
        "Other [zzz].mp4",
        "Talk (2).en.vtt",
        "Talk (2).mp4",
        "[abc123].jpg",
    ]
    assert (tmp_path / "Talk.mp4").read_bytes() == b"another talk"


def test_pictures_gallery_dl_zipped_are_swapped_for_their_zip(tmp_path: Path) -> None:
    """It deletes what it zipped; the job then holds the zip."""
    folder = tmp_path / "instagram" / "someone"
    folder.mkdir(parents=True)
    zipped = folder.with_name("someone.zip")
    zipped.write_bytes(b"")
    job = Job(url="https://example.com/g", mode="images", options=Options(zip=True))
    job.files = [str(folder / "1.jpg"), str(folder / "2.jpg")]
    find_zips(job)
    assert job.files == [str(zipped)]


def test_picked_pictures_share_one_removal_and_missing_ones_drop_out(
    queue: Queue, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The remover loads its models once, so a batch is one call with every picture still there."""
    pictures = [tmp_path / name for name in ("a.jpg", "b.png", "gone.webp")]
    for picture in pictures[:2]:
        picture.write_bytes(b"x")
    seen: list[list[Path]] = []

    def remove(_job: Job, found: Sequence[Path], _tier: str) -> Outcome:
        seen.append(list(found))
        return True, ""

    monkeypatch.setattr(textremoval, "remove_text", remove)
    job = Job(url=str(pictures[0]), mode="detext", options=Options(), job_kind="convert")
    job.pictures = [str(picture) for picture in pictures]
    assert queue.convert(job) == (True, "")
    assert seen == [pictures[:2]]
    assert job.title == "2 pictures"
