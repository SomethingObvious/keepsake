"""The library listing, the archives, the store and the update arithmetic."""

import sqlite3
from contextlib import closing
from pathlib import Path

from keepsake import library, store
from keepsake.updates import ffmpeg_version, version_in, version_tuple


def test_the_library_lists_media_newest_first(tmp_path: Path) -> None:
    """Sidecars and hidden or trashed files are left out, and folders are relative."""
    (tmp_path / "Youtube").mkdir()
    (tmp_path / "Youtube" / "a.mp4").write_bytes(b"x")
    (tmp_path / "Youtube" / ".trashed-1795653706-a.mp4").write_bytes(b"x")
    (tmp_path / "Youtube" / "a.info.json").write_text("{}", encoding="utf-8")
    (tmp_path / "b.jpg").write_bytes(b"xy")
    found = library.files(str(tmp_path))
    assert {entry["name"] for entry in found} == {"a.mp4", "b.jpg"}
    assert next(e for e in found if e["name"] == "a.mp4")["folder"] == "Youtube"
    assert library.files(str(tmp_path / "missing")) == []


def test_an_archive_can_forget_so_things_download_again(data: Path) -> None:
    """Text archives and gallery-dl's SQLite ones both."""
    text = data / "yt-dlp-archive.txt"
    text.write_text("youtube a\nyoutube b\n", encoding="utf-8")
    base = data / "gallery-dl-archive.sqlite3"
    with closing(sqlite3.connect(base)) as db, db:
        db.execute("CREATE TABLE archive (entry TEXT PRIMARY KEY)")
        db.executemany("INSERT INTO archive VALUES (?)", [("x1",), ("x2",)])
    listed = {entry["file"]: entry["entries"] for entry in library.archives()}
    assert listed == {"yt-dlp-archive.txt": 2, "gallery-dl-archive.sqlite3": 2}
    assert library.forget(text, ["youtube a"]) == 1
    assert library.entries(text) == ["youtube b"]
    assert library.forget(base, ["x2"]) == 1
    assert library.entries(base) == ["x1"]


def test_only_archives_in_the_data_folder_can_be_opened(data: Path, tmp_path: Path) -> None:
    """The window cannot point this at any file on the disk."""
    (data / "yt-dlp-archive.txt").write_text("", encoding="utf-8")
    outside = tmp_path / "secret.txt"
    outside.write_text("", encoding="utf-8")
    assert library.archive_path("yt-dlp-archive.txt") is not None
    assert library.archive_path("../secret.txt") is None
    assert library.archive_path(str(outside)) is None


def test_the_store_survives_a_damaged_file(tmp_path: Path) -> None:
    """A torn or wrong-shaped file gives the fallback, never an exception."""
    path = tmp_path / "x.json"
    store.save(path, [{"a": 1}, 2, "three"])
    assert store.load_list(path) == [{"a": 1}]
    path.write_text("{not json", encoding="utf-8")
    assert store.load(path, "fallback") == "fallback"
    assert store.record([1]) == {}
    assert store.items({"a": 1}) == []


def test_versions_are_compared_as_numbers_not_text() -> None:
    """1.10.0 is newer than 1.9.9, and main's version is read from its source."""
    assert version_tuple("1.2.3") == (1, 2, 3)
    assert version_tuple("nightly") is None
    assert (version_tuple("1.10.0") or ()) > (version_tuple("1.9.9") or ())
    assert version_in('"""Keepsake."""\n\n__version__ = "1.10.0"\nAPP = "Keepsake"\n') == "1.10.0"
    assert version_in("") is None


def test_ffmpeg_shows_its_release_or_a_nightly_build_date() -> None:
    """A nightly's version is its build date, since its own number starts with a bare N."""
    nightly = "ffmpeg version N-125875-g5d4d3bdc61-20260731 Copyright (c) 2000-2026"
    assert ffmpeg_version(nightly) == "2026.07.31"
    assert ffmpeg_version("ffmpeg version 7.1-full_build-www.gyan.dev Copyright") == "7.1"
    assert ffmpeg_version(None) is None


def test_a_saved_playlist_replaces_itself_in_order(data: Path) -> None:
    """Saving under an existing id swaps that entry, and values of the wrong type fall back."""
    first = library.save_playlist({"name": " Road trip ", "files": ["a.mp4", 3, "b.mp3"]})
    second = library.save_playlist({"name": "", "files": "nope", "at": True})
    assert [p["name"] for p in second] == ["Road trip", "Playlist"]
    assert first[0]["files"] == ["a.mp4", "b.mp3"]
    assert second[1]["files"] == []
    assert second[1]["at"] == 0
    road = str(first[0]["id"])
    library.save_playlist({"id": road, "name": "Drive", "files": ["b.mp3"], "at": 1})
    renamed = library.playlists()
    assert [p["name"] for p in renamed] == ["Drive", "Playlist"]
    assert renamed[0]["at"] == 1
    assert [p["name"] for p in library.delete_playlist(road)] == ["Playlist"]
    assert (data / "playlists.json").is_file()
