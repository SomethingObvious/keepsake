"""The eraser: the snap, the fill, undo, and saving a copy that changes only what was edited."""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import jpeglib
import numpy as np
import pytest
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFont, JpegImagePlugin

from keepsake import eraser

HEIGHT, WIDTH = 160, 480
ORIENTATION_SIDEWAYS = 6  # stored turned a quarter to the left
BLUR = 4  # how far past the text the overlay network's view reaches at full size, in pixels


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
    """Stands in for the overlay network: sure of the band the caption is in, nowhere else."""

    def run(
        self,
        _names: Sequence[str] | None,
        feed: Mapping[str, NDArray[np.float32] | NDArray[np.uint8]],
        /,
    ) -> list[NDArray[np.float32] | NDArray[np.uint8]]:
        """Return two logit maps the size of the input."""
        _, _, tall, wide = feed["image"].shape
        logits = np.full((1, 2, tall, wide), -9.0, dtype=np.float32)
        logits[:, :, int(tall * 0.3) : int(tall * 0.7), int(wide * 0.06) : int(wide * 0.92)] = 9.0
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


def seen(truth: NDArray[np.bool_]) -> NDArray[np.float32]:
    """Return the overlay network's view of some text: sure of it, and blurred past it."""
    return eraser.grow(truth, BLUR).astype(np.float32)


def test_a_stroke_snaps_to_the_caption_inside_it() -> None:
    """The caption's ink is kept, and the photo around it is not; with no network, nothing is."""
    picture, truth = captioned()
    stroke = np.zeros(truth.shape, dtype=bool)
    stroke[34:128, 16 : WIDTH - 16] = True  # painted well past the text, as a hand would
    assert (truth <= stroke).all()
    snapped = eraser.snap(picture, stroke, seen(truth))
    assert (snapped <= stroke).all()
    assert (snapped & truth).sum() / truth.sum() > 0.95
    assert snapped.sum() < 0.4 * stroke.sum()
    # Colour alone is not enough: what the network does not see as laid on top stays.
    assert not eraser.snap(picture, stroke, np.zeros(truth.shape, dtype=np.float32)).any()


def test_a_loose_stroke_does_not_flood_what_is_not_text() -> None:
    """A dark post and a bright edge inside a loose stroke stay, however unlike the ring."""
    picture, truth = captioned()
    picture[30:132, 300:330] = (12, 12, 12)  # a post the stroke crosses, starker than the caption
    picture[30:132, 360:364] = (250, 250, 250)  # and a bright edge
    stroke = np.zeros(truth.shape, dtype=bool)
    stroke[30:132, 8 : WIDTH - 8] = True
    snapped = eraser.snap(picture, stroke, seen(truth))
    # Only where the post touches the letters: within the network's blur, the gate and the halo.
    reach = BLUR + eraser.NEAR_NETWORK + eraser.HALO
    assert not (snapped & ~eraser.grow(truth, reach)).any()
    assert (snapped & truth).sum() / truth.sum() > 0.95


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


def test_without_jpeglib_a_jpeg_is_encoded_again_with_its_own_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The phone app has no jpeglib, so the copy is encoded again, keeping what the photo set."""
    monkeypatch.setitem(sys.modules, "jpeglib", None)
    original = tmp_path / "phone.jpg"
    exif = Image.Exif()
    exif[eraser.ORIENTATION] = ORIENTATION_SIDEWAYS
    Image.fromarray(photo()).save(original, quality=80, subsampling="4:4:4", exif=exif)
    opened = eraser.load(original)
    edited = opened.picture.copy()
    changed = np.zeros(edited.shape[:2], dtype=bool)
    changed[16:48, 24:56] = True
    edited[changed] = (255, 255, 255)
    copy = eraser.write(opened, edited, changed)
    assert copy.name == "phone (no text).jpg"
    with Image.open(original) as before, Image.open(copy) as after:
        assert isinstance(before, JpegImagePlugin.JpegImageFile)
        assert isinstance(after, JpegImagePlugin.JpegImageFile)
        assert after.quantization == before.quantization
        assert JpegImagePlugin.get_sampling(after) == JpegImagePlugin.get_sampling(before)
        assert after.getexif()[eraser.ORIENTATION] == ORIENTATION_SIDEWAYS
    again = eraser.load(copy).picture.astype(int)
    assert again[20:44, 28:52].min() > 230
    far = ~eraser.grow(changed, 24)
    assert np.abs(again[far] - opened.picture[far]).max() <= 2  # the same tables barely move it


def test_the_editor_suggests_removes_undoes_and_saves_a_copy(tmp_path: Path) -> None:
    """The network's caption is marked, Remove paints it, Undo undoes it, Save keeps the original.

    Little of the band the network is sure of is marked beside the caption itself.
    """
    picture, truth = captioned()
    original = tmp_path / "meme.png"
    Image.fromarray(picture).save(original)
    editor = eraser.Editor()
    editor.models = eraser.Models(Overlay(), Painter())
    shown = editor.open(original, tmp_path / "no models needed")
    assert (shown["width"], shown["height"]) == (WIDTH, HEIGHT)
    assert str(shown["picture"]).startswith("data:image/jpeg;base64,")
    assert editor.save() is None  # nothing changed yet
    assert editor.suggest() is not None
    assert (editor.mask & truth).sum() / truth.sum() > 0.9
    assert (editor.mask & ~eraser.grow(truth, 3)).sum() < 0.05 * editor.mask.sum()
    rows, cols = np.nonzero(truth)
    kept = (int(rows[cols > 300][0]), int(cols[cols > 300][0]))
    gone = (int(rows[(cols > 60) & (cols < 100)][0]), int(cols[(cols > 60) & (cols < 100)][0]))
    erased = editor.stroke([(50.0, 80.0), (110.0, 80.0)], 90.0, erase=True, snapped=True)
    assert erased is not None
    assert not editor.mask[gone]
    removed = editor.remove()
    assert removed is not None
    assert str(removed["picture"]).startswith("data:image/jpeg;base64,")
    assert not editor.mask.any()
    assert (editor.picture[kept] == 128).all()
    assert (editor.picture[gone] != 128).any()  # erased from the mark, so left alone
    editor.undo()
    assert (editor.picture == picture).all()
    assert editor.mask[kept]
    editor.remove()
    copy = editor.save()
    assert copy is not None
    assert copy.name == "meme (no text).png"
    assert (np.asarray(Image.open(copy)) == editor.picture).all()
    assert (np.asarray(Image.open(original)) == picture).all()
