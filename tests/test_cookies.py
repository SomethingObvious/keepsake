"""Which session a download uses, and the cookies.txt a sign-in window writes."""

from pathlib import Path

from keepsake import cookies
from keepsake.options import Options


def test_a_site_signed_into_from_keepsake_is_used_automatically(data: Path) -> None:
    """A sign-in for youtube.com covers music.youtube.com and youtu.be too."""
    jar = data / "cookies" / "youtube.com.txt"
    jar.parent.mkdir()
    jar.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    assert cookies.chosen(Options(), "https://music.youtube.com/watch?v=1") == ("file", str(jar))
    assert cookies.chosen(Options(), "https://youtu.be/abc") == ("file", str(jar))
    assert cookies.chosen(Options(), "https://vimeo.com/1") is None


def test_a_named_choice_always_wins() -> None:
    """A browser or a file the user chose is used; never means never."""
    assert cookies.chosen(Options(cookies="firefox"), "https://x.com/a") == ("browser", "firefox")
    assert cookies.chosen(Options(cookies="file", cookie_file="c.txt")) == ("file", "c.txt")
    assert cookies.chosen(Options(cookies="file")) is None
    assert cookies.chosen(Options(cookies="none"), "https://x.com/a") is None


def test_both_tools_take_the_same_flags() -> None:
    """A browser is borrowed; a file is read."""
    assert cookies.arguments(("browser", "edge")) == ["--cookies-from-browser", "edge"]
    assert cookies.arguments(("file", "c.txt")) == ["--cookies", "c.txt"]
    assert cookies.arguments(None) == []


def test_a_sign_in_is_written_as_netscape_cookies(data: Path) -> None:
    """HttpOnly cookies are marked, a leading dot covers subdomains, and it can be forgotten."""
    jar = data / "cookies" / "example.com.txt"
    cookies.write_jar(
        jar,
        [
            cookies.Cookie(
                "sid", "abc", ".example.com", "/", secure=True, httponly=True, expires=99
            ),
            cookies.Cookie(
                "pref", "1", "example.com", "", secure=False, httponly=False, expires=-5
            ),
        ],
    )
    lines = jar.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# Netscape HTTP Cookie File"
    assert "#HttpOnly_.example.com\tTRUE\t/\tTRUE\t99\tsid\tabc" in lines
    assert "example.com\tFALSE\t/\tFALSE\t0\tpref\t1" in lines
    assert cookies.sign_ins()[0]["cookies"] == 2
    cookies.forget("www.example.com")
    assert cookies.sign_ins() == []
