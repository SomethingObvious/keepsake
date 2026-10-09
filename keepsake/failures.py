"""Reading a failure, and saying what to do about it.

Ported from afterimage's fetch.rs, where each branch exists because a real
message was once answered with the wrong advice. A download fails six ways
that have nothing in common but the exit code, and the tools already say
which one happened, in prose.
"""

import re
from collections.abc import Callable

# A browser encrypting its cookie store so that only it can read it.
SEALED = ("dpapi", "failed to decrypt", "app-bound")
# A browser holding its cookie store open while it runs.
LOCKED = ("could not copy",)


def says(message: str, *needles: str) -> bool:
    """Return whether any of the phrases appears in the message, ignoring case."""
    low = message.lower()
    return any(needle in low for needle in needles)


def cookie_store_trouble(message: str) -> bool:
    """Return whether the browser would not hand over its session: the site was never asked."""
    return says(message, *SEALED, *LOCKED)


def needs_sign_in(message: str) -> bool:
    """Return whether the site wants to know who you are."""
    return says(
        message,
        "login required",
        "log in",
        "sign in",
        "cookies",
        "not a bot",
        "authentication",
        "account",
        "redirect to login",
    )


def bot_check(message: str) -> bool:
    """Return whether YouTube turned the request away as automated."""
    return says(message, "not a bot", "403", "forbidden", "po token", "sabr", "n challenge")


def unrecognised(message: str) -> bool:
    """Return whether the failure means 'that is not a video' rather than 'that went wrong'.

    "no video" is Instagram's and X's answer for a picture post, which is
    exactly the page the gallery side exists for.
    """
    return says(
        message,
        "unsupported url",
        "no video formats",
        "unable to extract",
        "no video",
        "no suitable extractor",
        "nothing was written",
    )


def transient(message: str) -> bool:
    """Return whether trying again later is likely to work."""
    return says(
        message,
        "429",
        "too many requests",
        "timed out",
        "temporarily",
        "connection reset",
        "connection aborted",
        "getaddrinfo",
        "name resolution",
        "502",
        "503",
        "504",
        "network is unreachable",
        "incomplete read",
    )


type Rule = tuple[Callable[[str], bool], str]


def any_of(*needles: str) -> Callable[[str], bool]:
    """Return a test for any of these phrases."""
    return lambda message: says(message, *needles)


# In order: the first rule that matches is the advice. Each sits where it does
# because a real message once matched an earlier, wrong one.
RULES: tuple[Rule, ...] = (
    (
        any_of(*SEALED),
        (
            "Chrome and the browsers built on it seal their cookies to themselves (since "
            "Chrome 127), so nothing else can read them. Sign in to the site from Keepsake "
            "instead (Settings > Sign-in), or choose Firefox there."
        ),
    ),
    (any_of(*LOCKED), "A browser is holding its cookie store open. Close it completely and retry."),
    (
        needs_sign_in,
        (
            "That page only shows this to someone signed in. Sign in to the site from Keepsake "
            "(Settings > Sign-in) and try again; it takes a minute and works where borrowing a "
            "browser's cookies does not."
        ),
    ),
    (
        any_of("private", "only available to", "members-only", "subscriber"),
        (
            "That is private, or kept for certain accounts. Signing in only helps if your "
            "account can already see it."
        ),
    ),
    (
        any_of("429", "rate-limit", "rate limit", "too many requests"),
        (
            "The site is asking this machine to slow down. Keepsake retries by itself after a "
            "pause; Settings > Network has a more careful pace if it keeps happening."
        ),
    ),
    (
        any_of("geo", "not available in your country", "blocked in"),
        (
            "The site will not serve that to this part of the world. A proxy somewhere else "
            "(Settings > Network) is the usual way round."
        ),
    ),
    (
        unrecognised,
        (
            "Neither yt-dlp nor gallery-dl found anything to download there. Either the site "
            "changed how it serves media, or the link has nothing on it. The nightly yt-dlp "
            "(Repair, or Settings > Tools) often knows about a change first."
        ),
    ),
    (
        any_of("unavailable", "removed", "has been deleted", "404", "does not exist"),
        "The site says it is gone.",
    ),
    # After "gone" on purpose: a 404 arrives as "unable to download webpage", and
    # sending someone to check their connection for a missing page is wrong.
    (
        bot_check,
        (
            "The site turned the request away. Repair clears yt-dlp's cache and tries again, "
            "then tries the nightly yt-dlp; signing in (Settings > Sign-in) is the next step "
            "if that is not enough."
        ),
    ),
    (
        any_of(
            "unable to download webpage",
            "getaddrinfo",
            "connection",
            "timed out",
            "name resolution",
            "network is unreachable",
            "ssl",
        ),
        "That looks like the connection rather than the page. Keepsake retries by itself.",
    ),
    (
        any_of("ffmpeg", "ffprobe", "postprocessing"),
        (
            "Merging or converting failed. Try Container: original, or turn off embedding "
            "under Options."
        ),
    ),
)
OTHERWISE = (
    "No more was said about why. If the site changed something recently, Repair usually fixes it."
)


def advice(message: str) -> str:
    """Return what to actually do about a failure, worked out from what the tool said."""
    return next((text for matches, text in RULES if matches(message)), OTHERWISE)


def plainly(message: str) -> str:
    """Return the site's own complaint, with the machinery filed off."""
    text = message.strip()
    for prefix in ("ERROR:", "error:", "WARNING:"):
        text = text.removeprefix(prefix).lstrip()
    text = re.sub(r"^(\[[^\]]+\])+\s*", "", text)
    head, separator, tail = text.partition(": ")
    if separator and " " not in head:
        text = tail  # the video id
    text = text.split(" (caused by")[0]
    text = text.split(". ")[0].strip().rstrip(".")
    if not text or cookie_store_trouble(message) or "github.com" in text:
        return ""
    return text[0].upper() + text[1:] + "."
