"""Where folder pickers start, when the folder in hand is not there yet."""

from pathlib import Path

from keepsake.api import nearest_folder


def test_a_folder_not_made_yet_never_strands_the_picker(tmp_path: Path) -> None:
    """A Keepsake folder not made yet starts the picker in the folder above it."""
    assert nearest_folder(str(tmp_path)) == tmp_path
    assert nearest_folder(str(tmp_path / "Keepsake" / "deeper")) == tmp_path
    assert nearest_folder("") is None
