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
