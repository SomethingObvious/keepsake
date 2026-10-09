"""Links out of pastes, command lines, dropped files and bookmarklets."""

from pathlib import Path

from keepsake.links import extract_urls, gallery_name, kind, links_from_args, site_of


def test_links_come_out_of_a_messy_paste() -> None:
    """Sentence punctuation is dropped; a Wikipedia title keeps its parentheses."""
    text = (
        "see https://a.com/x?y=1, and (https://b.org/z)\nytsearch3:lofi beats\nnothing\n"
        "https://en.wikipedia.org/wiki/Mercury_(planet)."
    )
    assert extract_urls(text) == [
        "https://a.com/x?y=1",
        "https://b.org/z",
        "ytsearch3:lofi beats",
        "https://en.wikipedia.org/wiki/Mercury_(planet)",
    ]


def test_the_same_link_twice_is_one_download() -> None:
    """Pasting a list with repeats does not download anything twice."""
    assert extract_urls("https://a.com/1\nhttps://a.com/1") == ["https://a.com/1"]


def test_a_bookmarklet_link_carries_its_mode(tmp_path: Path) -> None:
    """keepsake:// links name the page and optionally the mode; files hold lists of links."""
    listing = tmp_path / "links.txt"
    listing.write_text("one https://x.com/a\ntwo https://y.com/b\n", encoding="utf-8")
    found = links_from_args(
        [
            "keepsake://add?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dabc&mode=audio",
            "keepsake://add?url=https%3A%2F%2Fvimeo.com%2F1&mode=nonsense",
            str(listing),
        ]
    )
    assert found == [
        ("https://www.youtube.com/watch?v=abc", "audio"),
        ("https://vimeo.com/1", None),
        ("https://x.com/a", None),
        ("https://y.com/b", None),
    ]


def test_every_name_for_a_site_is_the_same_site() -> None:
    """Sign-ins and rules match however the link was written."""
    assert site_of("https://music.youtube.com/watch?v=1") == "youtube.com"
    assert site_of("https://youtu.be/abc") == "youtube.com"
    assert site_of("https://www.instagram.com/p/x/") == "instagram.com"
    assert site_of("twitter.com/someone") == "x.com"
    assert site_of("https://old.reddit.com/r/x") == "reddit.com"
    assert site_of("ytsearch5:cats") == ""


def test_files_are_sorted_by_what_they_hold() -> None:
    """The library shows pictures, video and sound; sidecar files are not media."""
    assert kind("a.MKV") == "video"
    assert kind("song.opus") == "audio"
    assert kind("x.webp") == "image"
    assert kind("clip.part") is None
    assert kind("clip.info.json") is None


def test_a_gallery_folder_is_named_from_its_link_one_level_deep() -> None:
    """The site, then whose it is; the words that only name a kind of page are dropped."""
    assert gallery_name("https://kemono.cr/patreon/user/78961792") == "kemono patreon 78961792"
    assert gallery_name("https://www.instagram.com/natgeo/") == "instagram natgeo"
    assert gallery_name("https://old.reddit.com/r/pics/") == "reddit pics"
    assert gallery_name("https://www.pixiv.net/en/users/123/artworks") == "pixiv 123"
    assert gallery_name("https://danbooru.donmai.us/posts?tags=cat_ears") == "danbooru cat_ears"
    assert gallery_name('https://x.com/a:b"c|d') == "x a b c d"


def test_a_file_path_with_brackets_is_no_site() -> None:
    """Conversions carry a path where a link would be, and [ reads as a broken IPv6 host."""
    assert site_of(r"C:\Users\me\Music\Keepsake\Song [Live].flac") == ""
    assert gallery_name("https://[broken/tag") == "gallery"
