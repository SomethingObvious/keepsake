"""What an installed copy does on its own: fetch its tools, and take in a release."""

import importlib.machinery
import importlib.util
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from keepsake import tools, updates

if TYPE_CHECKING:
    from collections.abc import Callable

STARTER = Path(__file__).resolve().parent.parent / "packaging" / "keepsake.pyw"


def zipped(path: Path, files: dict[str, str]) -> Path:
    """Write a zip holding these files, and return it."""
    with zipfile.ZipFile(path, "w") as bundle:
        for name, text in files.items():
            bundle.writestr(name, text)
    return path


def test_tools_are_found_anywhere_in_their_zip(tmp_path: Path) -> None:
    """FFmpeg's zip keeps them in a bin folder. They come out flat, and a missing one is named."""
    archive = zipped(
        tmp_path / "ffmpeg.zip",
        {"ffmpeg-master/bin/ffmpeg.exe": "f", "ffmpeg-master/LICENSE.txt": "l"},
    )
    folder = tmp_path / "tools"
    folder.mkdir()
    assert tools.take_out(archive, ("ffmpeg.exe", "ffprobe.exe"), folder) == ["ffprobe.exe"]
    assert (folder / "ffmpeg.exe").read_text(encoding="utf-8") == "f"


def test_release_notes_and_the_app_download_are_read() -> None:
    """The app zip is found by name among the release's files."""
    release: dict[str, object] = {
        "assets": [
            {
                "name": "KeepsakeSetup.exe",
                "browser_download_url": "https://example.com/setup",
            },
            {"name": "keepsake-app-1.17.0.zip", "browser_download_url": "https://example.com/app"},
        ],
    }
    assert updates.asset_url(release, "keepsake-app-1.17.0.zip") == "https://example.com/app"
    assert updates.asset_url(release, "keepsake-app-9.9.9.zip") == ""
    assert updates.release_notes("- Folded the options\n\n* Gave previews a player\n") == [
        "Folded the options",
        "Gave previews a player",
    ]


def test_an_update_unpacks_only_if_it_is_keepsake(tmp_path: Path) -> None:
    """A zip without the package is refused and leaves nothing behind."""
    good = zipped(tmp_path / "good.zip", {"keepsake/__init__.py": "", "ui/index.html": ""})
    updates.unpack_app(good.as_uri(), tmp_path / "app.next")
    assert (tmp_path / "app.next" / "ui" / "index.html").is_file()
    bad = zipped(tmp_path / "bad.zip", {"something/else.txt": ""})
    with pytest.raises(RuntimeError):
        updates.unpack_app(bad.as_uri(), tmp_path / "other.next")
    assert not (tmp_path / "other.next").exists()


def test_the_starter_swaps_in_an_update_or_leaves_the_app_alone(tmp_path: Path) -> None:
    """app.next becomes app. With no update waiting, app is left exactly as it was."""
    loader = importlib.machinery.SourceFileLoader("starter", str(STARTER))
    spec = importlib.util.spec_from_loader("starter", loader)
    assert spec is not None
    starter = importlib.util.module_from_spec(spec)
    loader.exec_module(starter)
    swap = cast("Callable[[Path], bool]", starter.swap_in_update)
    (tmp_path / "app" / "keepsake").mkdir(parents=True)
    (tmp_path / "app" / "old.txt").write_text("old", encoding="utf-8")
    assert not swap(tmp_path)
    assert (tmp_path / "app" / "old.txt").is_file()
    (tmp_path / "app.next" / "keepsake").mkdir(parents=True)
    (tmp_path / "app.next" / "keepsake" / "__init__.py").write_text("", encoding="utf-8")
    assert swap(tmp_path)
    assert (tmp_path / "app" / "keepsake" / "__init__.py").is_file()
    assert not (tmp_path / "app" / "old.txt").exists()
    assert not (tmp_path / "app.next").exists()
    assert not (tmp_path / "app.old").exists()
