"""Every test gets its own empty data folders, so nothing touches the real ones."""

from pathlib import Path

import pytest

from keepsake import paths


@pytest.fixture(autouse=True)
def data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the program's data folder at a fresh temporary one."""
    folder = tmp_path / "data"
    folder.mkdir()
    monkeypatch.setattr(paths, "DATA", folder)
    monkeypatch.setattr(paths, "TEXT_REMOVAL", tmp_path / "text-removal")
    return folder
