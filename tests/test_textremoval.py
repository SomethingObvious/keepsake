"""Setting the eraser up: two pinned models, checked, and nothing an older setup left."""

import hashlib
import urllib.request
from types import TracebackType
from typing import Self

import pytest

from keepsake import textremoval
from keepsake.jobs import Job
from keepsake.options import Options

NETWORK = bytes(range(256)) * 4096
PAINTER = b"mi-gan" * 1000


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


def pinned(name: str, data: bytes) -> textremoval.Download:
    """Return a download pinned to these bytes."""
    return textremoval.Download(
        f"https://example.test/{name}", name, len(data), hashlib.sha256(data).hexdigest()
    )


def setup_job() -> Job:
    """Return the job that sets the eraser up."""
    return Job(url="text-removal", mode="eraser", options=Options(), job_kind="setup")


def test_both_models_are_pinned_to_a_revision_and_a_hash() -> None:
    """Exactly two models, each from a fixed revision and checked against its SHA-256."""
    assert [f.to for f in textremoval.FILES] == ["overlay.onnx", "migan.onnx"]
    for want in textremoval.FILES:
        assert want.url.startswith("https://")
        assert textremoval.NETWORK_TAG in want.url or textremoval.MIGAN[1] in want.url
        assert len(want.sha256) == len(hashlib.sha256().hexdigest())


def test_a_download_resumes_and_is_checked_against_its_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """A partial file carries on from where it stopped; the whole must match the pinned hash."""
    want = pinned("model.onnx", NETWORK)
    target = textremoval.models() / "model.onnx"
    target.parent.mkdir(parents=True)
    target.with_name("model.onnx.part").write_bytes(NETWORK[:5000])
    asked: list[str] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> Reply:
        asked.append(request.get_header("Range") or "")
        assert timeout > 0
        return Reply(NETWORK, request)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert textremoval.fetch(want, setup_job(), 0, len(NETWORK)) == len(NETWORK)
    assert target.read_bytes() == NETWORK
    assert asked == ["bytes=5000-"]
    wrong = textremoval.Download(want.url, "other.onnx", len(NETWORK), "0" * 64)
    with pytest.raises(ValueError, match="pinned hash"):
        textremoval.fetch(wrong, setup_job(), 0, len(NETWORK))
    assert not (textremoval.models() / "other.onnx").exists()


def test_setup_clears_out_an_older_setup_and_fetches_both_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The old Python, LaMa, the judges and their markers go; the network already there stays."""
    home, models = textremoval.home(), textremoval.models()
    for old in ("env/Scripts/python.exe", "models/judge-small/model.gguf", "models/ocr/det.onnx"):
        (home / old).parent.mkdir(parents=True, exist_ok=True)
        (home / old).write_bytes(b"old")
    (models / "lama.onnx").write_bytes(b"old")
    (home / "quick.ready").write_text("1", encoding="utf-8")
    (models / "overlay.onnx").write_bytes(NETWORK)
    files = (pinned("overlay.onnx", NETWORK), pinned("migan.onnx", PAINTER))
    monkeypatch.setattr(textremoval, "FILES", files)
    served = {"https://example.test/migan.onnx": PAINTER}

    def urlopen(request: urllib.request.Request, timeout: float) -> Reply:
        assert timeout > 0
        return Reply(served[request.full_url], request)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert not textremoval.ready()
    assert textremoval.set_up(setup_job()) == (True, "")
    assert textremoval.ready()
    assert sorted(path.name for path in home.iterdir()) == ["models", "ready"]
    assert sorted(path.name for path in models.iterdir()) == ["migan.onnx", "overlay.onnx"]
    assert (models / "migan.onnx").read_bytes() == PAINTER


def test_an_older_setup_is_not_ready() -> None:
    """A marker from another version of setup means setting it up again."""
    textremoval.home().mkdir(parents=True)
    textremoval.marker().write_text("1", encoding="utf-8")
    assert not textremoval.ready()
    textremoval.forget()
    assert not textremoval.home().exists()
