"""The eraser: the snap, the fill, undo, and saving a copy that changes only what was edited."""

from collections.abc import Mapping, Sequence
from pathlib import Path

import jpeglib
import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFont

from keepsake import eraser

HEIGHT, WIDTH = 160, 480
ORIENTATION_SIDEWAYS = 6  # stored turned a quarter to the left


def photo(height: int = HEIGHT, width: int = WIDTH) -> NDArray[np.uint8]:
    """Return a busy picture: gradients and noise, so no region is one flat colour."""
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    smooth = np.stack([40 + x / 4, 70 + y / 2, 140 - x / 8], axis=2)
    noise = np.random.default_rng(1).normal(0, 12, (height, width, 3))
    return np.clip(smooth + noise, 0, 255).astype(np.uint8)


def captioned() -> tuple[NDArray[np.uint8], NDArray[np.bool_]]:
    """Return the photo with a white caption in a dark outline, and where the caption is."""
    layer = Image.new("RGBA", (WIDTH, HEIGHT))
    font = ImageFont.load_default(size=44)
    ImageDraw.Draw(layer).text(
        (40, 52), "best day ever", font=font, fill="white", stroke_width=3, stroke_fill="black"
    )
    picture = Image.alpha_composite(Image.fromarray(photo()).convert("RGBA"), layer)
    truth = np.asarray(layer.getchannel("A")) > 0
    return np.asarray(picture.convert("RGB")).copy(), truth


class Overlay:
    """Stands in for the overlay network: sure of a block at the top left, nowhere else."""

    def run(
        self,
        _names: Sequence[str] | None,
        feed: Mapping[str, NDArray[np.float32] | NDArray[np.uint8]],
        /,
    ) -> list[NDArray[np.float32] | NDArray[np.uint8]]:
        """Return two logit maps the size of the input."""
        _, _, tall, wide = feed["image"].shape
        logits = np.full((1, 2, tall, wide), -9.0, dtype=np.float32)
        logits[:, :, : tall // 4, : wide // 4] = 9.0
        return [logits]


class Painter:
    """Stands in for MI-GAN: paints every hole flat grey, and keeps every known pixel."""

    def __init__(self) -> None:
        """Count the crops it is handed."""
        self.crops = 0

    def run(
        self,
        _names: Sequence[str] | None,
        feed: Mapping[str, NDArray[np.float32] | NDArray[np.uint8]],
        /,
    ) -> list[NDArray[np.float32] | NDArray[np.uint8]]:
        """Return the image with its holes (mask 0) grey."""
        self.crops += 1
        image, mask = feed["image"].copy(), feed["mask"]
        image[np.broadcast_to(mask == 0, image.shape)] = 128
        return [image]


def test_a_stroke_snaps_to_the_caption_inside_it() -> None:
    """Every bit of the caption's ink is kept, and much of the photo around it is not."""
    picture, truth = captioned()
    stroke = np.zeros(truth.shape, dtype=bool)
    stroke[34:128, 16 : WIDTH - 16] = True  # painted well past the text, as a hand would
    assert (truth <= stroke).all()
    snapped = eraser.snap(picture, stroke, np.zeros(truth.shape, dtype=np.float32))
    assert (snapped <= stroke).all()
    assert (snapped & truth).sum() / truth.sum() > 0.99
    assert snapped.sum() < 0.4 * stroke.sum()
    # Whatever the overlay network is sure of counts too, but only inside the stroke.
    sure = np.zeros(truth.shape, dtype=np.float32)
    sure[110:150, 200:260] = 1.0
    with_network = eraser.snap(picture, stroke, sure)
    assert with_network[110:128, 200:260].all()
    assert not with_network[128:150].any()


def test_remove_paints_only_the_marked_part_one_patch_at_a_time() -> None:
    """The picture keeps its size, every marked pixel changes, every other one stays."""
    picture = photo()
    hole = np.zeros(picture.shape[:2], dtype=bool)
    hole[20:40, 30:90] = True
    hole[110:130, 380:450] = True
    painter = Painter()
    painted = eraser.fill(painter, picture, hole)
    assert painted.shape == picture.shape
    assert (painted[hole] == 128).all()
    assert (painted[~hole] == picture[~hole]).all()
    assert painter.crops == len(eraser.patches(hole)) == 2


def test_a_spliced_jpeg_keeps_every_block_the_edit_did_not_touch(tmp_path: Path) -> None:
    """Untouched blocks keep their coefficients, so no generation loss outside the edit."""
    original = tmp_path / "original.jpg"
    Image.fromarray(photo()).save(original, quality=85)
    decoded = np.asarray(Image.open(original).convert("RGB")).copy()
    changed = np.zeros(decoded.shape[:2], dtype=bool)
    changed[40:50, 40:60] = True
    decoded[changed] = (255, 0, 0)
    target = tmp_path / "cleaned.jpg"
    eraser.splice_jpeg(original, decoded, changed, target, tmp_path / "blocks.jpg")
    before, after = jpeglib.read_dct(str(original)), jpeglib.read_dct(str(target))
    touched = eraser.blocks_touched(changed, before.Y.shape, (1, 1))
    assert (before.Y[~touched] == after.Y[~touched]).all()
    assert not (before.Y[touched] == after.Y[touched]).all()
    far = ~eraser.grow(changed, 24)
    shown_before = np.asarray(Image.open(original).convert("RGB"))
    shown_after = np.asarray(Image.open(target).convert("RGB"))
    assert (shown_before[far] == shown_after[far]).all()


def test_a_sideways_photo_is_edited_upright_and_saved_the_way_it_is_stored(
    tmp_path: Path,
) -> None:
    """A phone photo is shown upright; the copy keeps the original's blocks and orientation."""
    original = tmp_path / "phone.jpg"
    exif = Image.Exif()
    exif[eraser.ORIENTATION] = ORIENTATION_SIDEWAYS
    Image.fromarray(photo()).save(original, quality=90, exif=exif)
    opened = eraser.load(original)
    assert opened.picture.shape[:2] == (WIDTH, HEIGHT)
    edited = opened.picture.copy()
    changed = np.zeros(edited.shape[:2], dtype=bool)
    changed[16:48, 24:56] = True  # the top left of the picture as shown
    edited[changed] = (255, 255, 255)
    copy = eraser.write(opened, edited, changed)
    assert copy.name == "phone (no text).jpg"
    with Image.open(copy) as saved:
        assert saved.getexif()[eraser.ORIENTATION] == ORIENTATION_SIDEWAYS
    again = eraser.load(copy).picture.astype(int)
    assert again[20:44, 28:52].min() > 230
    before, after = jpeglib.read_dct(str(original)), jpeglib.read_dct(str(copy))
    turned = eraser.stored(changed.astype(np.uint8), ORIENTATION_SIDEWAYS) > 0
    touched = eraser.blocks_touched(turned, before.Y.shape, (1, 1))
    assert (before.Y[~touched] == after.Y[~touched]).all()


def test_the_editor_suggests_removes_undoes_and_saves_a_copy(tmp_path: Path) -> None:
    """The network's guess is marked, Remove paints it, Undo undoes it, Save leaves the original."""
    original = tmp_path / "meme.png"
    Image.fromarray(photo()).save(original)
    editor = eraser.Editor()
    editor.models = eraser.Models(Overlay(), Painter())
    shown = editor.open(original, tmp_path / "no models needed")
    assert (shown["width"], shown["height"]) == (WIDTH, HEIGHT)
    assert str(shown["picture"]).startswith("data:image/jpeg;base64,")
    assert editor.save() is None  # nothing changed yet
    guess = editor.suggest()
    assert guess is not None
    assert editor.mask[: HEIGHT // 4, : WIDTH // 4].all()
    erased = editor.stroke([(10.0, 10.0), (40.0, 10.0)], 12.0, erase=True, snapped=True)
    assert erased is not None
    assert not editor.mask[10, 25]
    removed = editor.remove()
    assert removed is not None
    assert str(removed["picture"]).startswith("data:image/jpeg;base64,")
    assert not editor.mask.any()
    assert (editor.picture[30, 30] == 128).all()
    assert (editor.picture[10, 25] != 128).any()  # erased from the mark, so left alone
    editor.undo()
    assert (editor.picture == photo()).all()
    assert editor.mask[30, 30]
    editor.remove()
    copy = editor.save()
    assert copy is not None
    assert copy.name == "meme (no text).png"
    assert (np.asarray(Image.open(copy)) == editor.picture).all()
    assert (np.asarray(Image.open(original)) == photo()).all()
