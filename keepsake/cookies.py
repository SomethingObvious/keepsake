"""Signing in: a browser's session, a cookies.txt, or a site signed into from Keepsake."""

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
from pathlib import Path

from keepsake import paths
from keepsake.links import site_of
from keepsake.options import Options

type Credentials = tuple[str, str]  # ("browser", "firefox") or ("file", "C:\\...\\c.txt")

# Where each browser keeps the cookies a download would borrow, on Windows.
# Firefox is given its profiles directory, because which profile is live is
# written in a config the downloader already reads.
STORES = {
    "firefox": ("APPDATA", "Mozilla/Firefox/Profiles"),
    "chrome": ("LOCALAPPDATA", "Google/Chrome/User Data/Default/Network/Cookies"),
    "edge": ("LOCALAPPDATA", "Microsoft/Edge/User Data/Default/Network/Cookies"),
    "brave": ("LOCALAPPDATA", "BraveSoftware/Brave-Browser/User Data/Default/Network/Cookies"),
    "vivaldi": ("LOCALAPPDATA", "Vivaldi/User Data/Default/Network/Cookies"),
    "opera": ("APPDATA", "Opera Software/Opera Stable/Network/Cookies"),
    "chromium": ("LOCALAPPDATA", "Chromium/User Data/Default/Network/Cookies"),
}


def browsers() -> list[str]:
    """Return browsers with a session worth borrowing, most recently used first.

    The stores are only ever stat'ed, never read: reading them is the downloader's job.
    """
    found: list[tuple[float, str]] = []
    for name, (variable, rest) in STORES.items():
        base = os.environ.get(variable)
        if base:
            try:
                found.append((Path(base, rest).stat().st_mtime, name))
            except OSError:
                continue
    return [name for _, name in sorted(found, reverse=True)]


def jars() -> Path:
    """Return the folder holding sign-ins made from Keepsake's own window."""
    return paths.DATA / "cookies"


def site_jar(url: str) -> Path | None:
    """Return a sign-in made from Keepsake for this site, or for a parent domain of it."""
    parts = site_of(url).split(".")
    for start in range(len(parts) - 1):
        jar = jars() / (".".join(parts[start:]) + ".txt")
        if jar.is_file():
            return jar
    return None


def chosen(options: Options, url: str = "") -> Credentials | None:
    """Return the credentials a download should start with."""
    if options.cookies == "file":
        return ("file", options.cookie_file) if options.cookie_file else None
    if options.cookies == "none":
        return None
    if options.cookies == "auto":
        # A site signed into from Keepsake's own window is the one session that
        # always works: nothing is sealed, and nobody has to close a browser.
        jar = site_jar(url) if url else None
        return ("file", str(jar)) if jar else None
    return ("browser", options.cookies)


def arguments(credentials: Credentials | None) -> list[str]:
    """Return the command-line arguments for a set of credentials; both tools take the same."""
    if not credentials:
        return []
    how, value = credentials
    return ["--cookies-from-browser" if how == "browser" else "--cookies", value]


@dataclass(frozen=True, slots=True)
class Cookie:
    """One cookie, as a sign-in window saw it."""

    name: str
    value: str
    domain: str
    path: str
    secure: bool
    httponly: bool
    expires: int

    def line(self) -> str:
        """Return the cookie as a Netscape cookies.txt line."""
        return "\t".join(
            [
                ("#HttpOnly_" if self.httponly else "") + self.domain,
                "TRUE" if self.domain.startswith(".") else "FALSE",
                self.path or "/",
                "TRUE" if self.secure else "FALSE",
                str(max(0, self.expires)),
                self.name,
                self.value,
            ]
        )


def from_browser_window(jars_seen: Iterable[SimpleCookie]) -> list[Cookie]:
    """Flatten what pywebview hands back into cookies."""
    found: list[Cookie] = []
    for jar in jars_seen:
        for name, morsel in jar.items():
            try:
                expires = int(parsedate_to_datetime(morsel["expires"]).timestamp())
            except (TypeError, ValueError, OverflowError, IndexError):
                expires = 0
            found.append(
                Cookie(
                    name=name,
                    value=morsel.value,
                    domain=morsel["domain"],
                    path=morsel["path"],
                    secure=bool(morsel["secure"]),
                    httponly=bool(morsel["httponly"]),
                    expires=expires,
                )
            )
    return found


def write_jar(path: Path, cookies: Iterable[Cookie]) -> None:
    """Write Netscape cookies.txt, the format both tools read."""
    lines = ["# Netscape HTTP Cookie File", "# Written by Keepsake from its sign-in window.", ""]
    lines += [cookie.line() for cookie in cookies]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sign_ins() -> list[Mapping[str, object]]:
    """Return the sites signed into from Keepsake, with when and how many cookies."""
    if not jars().is_dir():
        return []
    found: list[Mapping[str, object]] = []
    for jar in sorted(jars().glob("*.txt")):
        rows = [
            line
            for line in jar.read_text(encoding="utf-8").splitlines()
            if line and (not line.startswith("#") or line.startswith("#HttpOnly_"))
        ]
        found.append({"site": jar.stem, "saved": jar.stat().st_mtime, "cookies": len(rows)})
    return found


def forget(site: str) -> None:
    """Delete a sign-in made from Keepsake."""
    jar = jars() / f"{site_of(site)}.txt"
    if jar.parent == jars() and jar.is_file():
        jar.unlink()
