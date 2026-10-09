"""Each kind of refusal is answered with its own remedy (cases from afterimage's fetch.rs)."""

import pytest

from keepsake.failures import advice, bot_check, needs_sign_in, plainly, transient, unrecognised


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("ERROR: [Instagram] ABC: login required", "signed in"),
        ("ERROR: [youtube] xyz: Sign in to confirm you're not a bot", "signed in"),
        ("ERROR: Failed to decrypt with DPAPI", "Firefox"),
        ("ERROR: Could not copy Chrome cookie database", "Close it"),
        ("ERROR: [instagram] def: This video is private", "private"),
        ("ERROR: HTTP Error 429: Too Many Requests", "slow down"),
        ("ERROR: [generic] Unsupported URL: https://example.com/", "Neither yt-dlp"),
        ("ERROR: [generic] x: Unable to download webpage: HTTP Error 404: Not Found", "gone"),
        ("ERROR: [youtube] x: HTTP Error 403: Forbidden", "turned the request away"),
        ("ERROR: Unable to download webpage: [Errno 11001] getaddrinfo failed", "connection"),
        ("ERROR: Postprocessing: ffmpeg exited with code 1", "Merging"),
        ("ERROR: something nobody has classified", "No more was said"),
    ],
)
def test_each_refusal_names_its_own_remedy(message: str, expected: str) -> None:
    """A login wall is never answered with 'update', nor a missing page with 'connection'."""
    assert expected in advice(message)


def test_a_cookie_store_that_will_not_open_is_not_a_login_wall() -> None:
    """Both mention cookies; neither is the site asking who you are."""
    assert "Close it" in advice("ERROR: Could not copy Chrome cookie database")
    assert plainly("ERROR: Failed to decrypt with DPAPI") == ""


def test_only_a_page_with_no_video_hands_over_to_the_gallery() -> None:
    """Which error survives decides what the user is told."""
    assert unrecognised("ERROR: Unsupported URL: https://example.com/photo")
    assert unrecognised("[gallery-dl][error] No suitable extractor found for 'x'")
    assert unrecognised("ERROR: [Instagram] abc: There is no video in this post")
    assert not unrecognised("ERROR: [Instagram] login required")
    assert not unrecognised("ERROR: HTTP Error 429: Too Many Requests")


def test_signing_in_is_told_from_other_failures() -> None:
    """Only a sign-in failure sends Keepsake hunting for a browser session."""
    assert needs_sign_in("ERROR: [Instagram] DM0J: HTTP redirect to login page")
    assert not needs_sign_in("ERROR: This video is private")


def test_flaky_failures_are_worth_retrying_and_refusals_are_repairable() -> None:
    """Dropped connections are retried by themselves; a 403 gets the repair button."""
    assert transient("ERROR: HTTP Error 429: Too Many Requests")
    assert transient("ERROR: Read timed out")
    assert not transient("ERROR: Video unavailable")
    assert bot_check("ERROR: [youtube] abc: HTTP Error 403: Forbidden")


def test_what_the_site_said_is_the_sentence_not_the_machinery() -> None:
    """Bracketed extractor names, ids and exception classes are filed off."""
    message = "ERROR: [youtube] abc: Video unavailable. This video is private (caused by X)"
    assert plainly(message) == "Video unavailable."
    assert plainly("[twitter][error] AuthRequired: login needed") == "Login needed."
