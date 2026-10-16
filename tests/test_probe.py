"""What the preview says about a link before it downloads."""

from keepsake import probe
from keepsake.options import Options


def test_saved_as_matches_the_name_the_download_ends_with() -> None:
    """Clean files lose the ID from their names, so the preview leaves it out too."""
    info = {"id": "jNQXAC9IVRw", "title": "Me at the zoo", "ext": "mp4"}
    assert probe.filename(info, Options()) == "Me at the zoo.mp4"
    assert probe.filename(info, Options(strip_metadata=False)) == "Me at the zoo [jNQXAC9IVRw].mp4"
    assert (
        probe.filename({**info, "title": ""}, Options(template="[%(id)s].%(ext)s"))
        == "[jNQXAC9IVRw].mp4"
    )


def test_a_slow_computer_gets_a_lighter_preview_that_still_knows_its_length() -> None:
    """A slow computer can take 144p, the sound alone, or no player, and the size is still known."""
    formats = [
        {
            "url": f"https://v/{h}",
            "vcodec": "avc1.4d",
            "acodec": "none",
            "ext": "mp4",
            "protocol": "https",
            "height": h,
        }
        for h in (144, 240, 360, 720)
    ] + [
        {
            "url": "https://a/low",
            "vcodec": "none",
            "acodec": "opus",
            "ext": "webm",
            "protocol": "https",
            "abr": 50,
        }
    ]
    info: dict[str, object] = {
        "id": "x",
        "title": "t",
        "ext": "mp4",
        "duration": 10,
        "formats": formats,
    }
    shown = {
        playback: probe.summarise_video(info, Options(preview_playback=playback))
        for playback in ("360", "144", "sound", "off")
    }
    assert (shown["360"]["watch"], shown["360"]["listen"]) == ("https://v/360", "https://a/low")
    assert shown["144"]["watch"] == "https://v/144"
    assert (shown["sound"]["watch"], shown["sound"]["listen"]) == ("https://a/low", "")
    assert (shown["off"]["watch"], shown["off"]["listen"]) == ("", "")
    assert shown["off"]["duration"] == 10


def test_a_wide_film_previews_at_its_own_360p_not_the_next_size_up() -> None:
    """YouTube's 360p of a 2.39:1 film is 358 pixels tall, and its label says what it is."""
    formats = [
        {
            "url": f"https://v/{note}",
            "vcodec": "avc1.4d",
            "acodec": "none",
            "ext": "mp4",
            "protocol": "https",
            "height": h,
            "format_note": note,
        }
        for h, note in ((178, "240p"), (358, "360p"), (536, "720p"))
    ]
    info: dict[str, object] = {"formats": formats}
    picked = {height: probe.watchable(info, height) for height in (360, 240)}
    assert {height: (f or {}).get("url") for height, f in picked.items()} == {
        360: "https://v/360p",
        240: "https://v/240p",
    }
