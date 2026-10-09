"""Subscriptions: cheap checks that stop at what is already there."""

import time
from pathlib import Path

from keepsake.options import Options
from keepsake.subscriptions import Subscription, Subscriptions, overrides_from


def test_a_check_stops_at_the_first_video_it_already_has() -> None:
    """Channels list newest first, so a known video, or an old one, ends the check."""
    sub = Subscription(url="https://www.youtube.com/@x/videos", name="X", since="20260901")
    extra = sub.ytdlp_extra()
    assert "--break-on-existing" in extra
    assert "--lazy-playlist" in extra
    assert extra[extra.index("--break-match-filters") + 1] == "upload_date>=20260901"
    assert "--break-match-filters" not in Subscription(url="u", name="n", start="all").ytdlp_extra()


def test_a_gallery_check_stops_after_three_known_files() -> None:
    """gallery-dl's abort, plus the start date as a filter it understands."""
    extra = Subscription(url="u", name="n", since="20260901").gallery_extra()
    assert extra[:2] == ["-A", "3"]
    assert extra[-1] == "date >= datetime(2026, 9, 1)"


def test_a_check_downloads_into_its_own_folder_as_a_playlist() -> None:
    """Named after the subscription, with dates in front so they sort."""
    sub = Subscription(url="u", name='Talk: "show" / 2', overrides={"quality": "720"})
    options = sub.options(Options(folder="D:/Media", quality="best"))
    assert Path(options.folder) == Path("D:/Media") / "Talk_ _show_ _ 2"
    assert options.playlist is True
    assert options.quality == "720"
    assert options.template.startswith("%(upload_date")


def test_it_is_due_only_when_its_interval_has_passed() -> None:
    """A paused subscription is never due."""
    now = time.time()
    sub = Subscription(url="u", name="n", every=6.0, checked=now - 7 * 3600)
    assert sub.due(now)
    assert not Subscription(url="u", name="n", checked=now - 3600).due(now)
    assert not Subscription(url="u", name="n", enabled=False).due(now)


def test_subscriptions_are_kept_and_counted(data: Path) -> None:
    """Adding, checking, changing and removing all survive a restart."""
    subs = Subscriptions()
    made = subs.add({"url": "https://example.com/feed", "name": "", "every": 3})
    assert made is not None
    assert made.name == "example.com/feed"
    assert subs.add({"url": "not a link", "name": "x"}) is None
    subs.checked(made.id, new=4, error="")
    subs.update(made.id, {"enabled": False})
    again = Subscriptions()
    assert again.items[0].found == 4
    assert again.items[0].enabled is False
    assert (data / "subscriptions.json").is_file()
    again.remove(made.id)
    assert Subscriptions().items == []


def test_a_damaged_record_is_dropped_not_fatal() -> None:
    """A record missing its link is skipped; a wrong-typed field keeps its default."""
    assert Subscription.load({"name": "no url"}) is None
    loaded = Subscription.load({"url": "u", "name": "n", "every": 3, "enabled": "yes"})
    assert loaded is not None
    assert loaded.every == 3.0
    assert loaded.enabled is True


def test_a_subscription_may_only_override_the_shape_of_a_download() -> None:
    """Never where files go, and never anything that is not a setting."""
    kept = overrides_from({"quality": "720", "folder": "C:/", "nonsense": 1, "skip_shorts": True})
    assert kept == {"quality": "720", "skip_shorts": True}
    assert overrides_from("nope") == {}
