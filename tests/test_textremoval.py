"""Setting the text remover up, and putting the pictures it cleaned where they go."""

import hashlib
import json
import os
import urllib.request
from pathlib import Path
from types import TracebackType
from typing import Self

import pytest

from keepsake import textremoval, winapi
from keepsake.jobs import Job
from keepsake.options import Options

WHEN = 1_000_000_000


def job(**changes: object) -> Job:
    """Return a job that removes text with the quick tier."""
    return Job(url="https://example.test/p/1", mode="images", options=Options().but(changes))


class Reply:
    """What urlopen hands back: a status, and the bytes from where the request asked."""

    def __init__(self, data: bytes, request: urllib.request.Request) -> None:
        """Serve `data`, from the Range the request carries if any."""
        wanted = request.get_header("Range") or "bytes=0-"
        self.start = int(wanted.removeprefix("bytes=").split("-")[0])
        self.status = 206 if self.start else 200
        self.data = data[self.start :]

    def read(self, size: int) -> bytes:
        """Return the next chunk."""
        chunk, self.data = self.data[:size], self.data[size:]
        return chunk

    def __enter__(self) -> Self:
        """Open."""
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Close."""


def test_a_tier_is_ready_only_when_this_version_of_setup_finished_it() -> None:
    """No marker, or one from an older setup, means set it up again."""
    assert not textremoval.ready("quick")
    textremoval.home().mkdir(parents=True)
    textremoval.marker("quick").write_text("0", encoding="utf-8")
    assert not textremoval.ready("quick")
    textremoval.marker("quick").write_text(textremoval.SETUP_VERSION, encoding="utf-8")
    assert textremoval.ready("quick")
    assert not textremoval.ready("best")


def test_only_the_best_tier_installs_pytorch() -> None:
    """The quick tier stays small: no PyTorch, no CUDA."""
    quick = [part for command in textremoval.packages_for("quick") for part in command]
    best = [part for command in textremoval.packages_for("best") for part in command]
    assert not any(part.startswith("torch") for part in quick)
    assert any(part.startswith("torch==") for part in best)
    assert textremoval.TORCH_INDEX in best


def test_a_cleaned_download_takes_the_originals_place_and_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """As it downloads, the original goes to the Recycle Bin and the cleaned one takes its place."""
    original = tmp_path / "picture.jpg"
    original.write_bytes(b"with text")
    os.utime(original, (WHEN, WHEN))
    cleaned = tmp_path / "picture.cleaned.jpg"
    cleaned.write_bytes(b"without")
    binned: list[bytes] = []

    def recycle(path: Path) -> bool:
        binned.append(path.read_bytes())
        path.unlink()
        return True

    monkeypatch.setattr(winapi, "recycle", recycle)
    running = job()
    reader = textremoval.Progress(running)
    reader(json.dumps({"stage": "Removing added text", "done": 1, "total": 4}))
    assert running.pct == 25.0
    assert running.stage == "Removing added text"
    reader(
        json.dumps(
            {
                "file": str(original),
                "status": "cleaned",
                "output": str(cleaned),
                "removed": ["golden hour"],
                "unsure": ["BOULEVARD"],
            }
        )
    )
    assert original.read_bytes() == b"without"
    assert not cleaned.exists()
    assert binned == [b"with text"]
    assert original.stat().st_mtime == WHEN
    assert reader.cleaned == 1
    assert any('"golden hour"' in line for line in running.log)
    assert any('"BOULEVARD" left' in line for line in running.log)


def test_a_picture_cleaned_in_the_library_is_saved_beside_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pressing the button never touches the original: the cleaned copy gets a name of its own."""
    original = tmp_path / "picture.jpg"
    original.write_bytes(b"with text")
    (tmp_path / "picture (no text).jpg").write_bytes(b"an earlier copy")
    cleaned = tmp_path / "picture.cleaned.jpg"
    cleaned.write_bytes(b"without")

    def recycle(path: Path) -> bool:
        pytest.fail(f"{path.name} went to the Recycle Bin")

    monkeypatch.setattr(winapi, "recycle", recycle)
    running = Job(url=str(original), mode="detext", options=Options(), job_kind="convert")
    reader = textremoval.Progress(running)
    said = {"file": str(original), "status": "cleaned", "output": str(cleaned), "removed": ["hi"]}
    reader(json.dumps(said))
    copy = tmp_path / "picture (no text 2).jpg"
    assert original.read_bytes() == b"with text"
    assert copy.read_bytes() == b"without"
    assert not cleaned.exists()
    assert running.files == [str(copy)]
    assert reader.cleaned == 1


def test_a_download_resumes_and_is_checked_against_its_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """A partial file carries on from where it stopped; the whole must match the pinned hash."""
    data = bytes(range(256)) * 4096
    pinned = textremoval.Download(
        "https://example.test/model.onnx", "model.onnx", len(data), hashlib.sha256(data).hexdigest()
    )
    target = textremoval.models() / "model.onnx"
    target.parent.mkdir(parents=True)
    target.with_name("model.onnx.part").write_bytes(data[:5000])
    asked: list[str] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> Reply:
        asked.append(request.get_header("Range") or "")
        assert timeout > 0
        return Reply(data, request)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    running = job()
    assert textremoval.fetch(pinned, running, 0, len(data)) == len(data)
    assert target.read_bytes() == data
    assert asked == ["bytes=5000-"]
    wrong = textremoval.Download(pinned.url, "other.onnx", len(data), "0" * 64)
    with pytest.raises(ValueError, match="pinned hash"):
        textremoval.fetch(wrong, running, 0, len(data))
    assert not (textremoval.models() / "other.onnx").exists()


def test_nothing_runs_until_a_tier_is_set_up(tmp_path: Path) -> None:
    """A download still succeeds; its log says where to set text removal up."""
    picture = tmp_path / "a.jpg"
    picture.write_bytes(b"x")
    running = job(remove_text="quick")
    assert textremoval.remove_text(running, [picture], "quick") == (True, "")
    assert any("not set up" in line for line in running.log)
    assert textremoval.remove_text(running, [picture], "off") == (True, "")
