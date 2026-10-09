"""Moving in what the app left under its old name."""

from keepsake.former import rewritten

OLD = r"C:\Users\me\Videos\Siphon"
NEW = r"C:\Users\me\Videos\Keepsake"
MOVES = [(OLD, NEW), ("file:///C:/Users/me/Videos/Siphon", "file:///C:/Users/me/Videos/Keepsake")]


def test_paths_move_with_their_folder() -> None:
    """A path or file link in the folder moves, in any case. One only starting the same stays."""
    saved = {
        "folder": OLD,
        "files": [OLD.lower() + r"\Me at the zoo.mp4", OLD + r" Old\a.mp4"],
        "thumb": "file:///C:/Users/me/Videos/Siphon/a%20b/1.jpg",
        OLD + r"\b.mp4": 12.5,
        "count": 3,
    }
    assert rewritten(saved, MOVES) == {
        "folder": NEW,
        "files": [NEW + r"\Me at the zoo.mp4", OLD + r" Old\a.mp4"],
        "thumb": "file:///C:/Users/me/Videos/Keepsake/a%20b/1.jpg",
        NEW + r"\b.mp4": 12.5,
        "count": 3,
    }
