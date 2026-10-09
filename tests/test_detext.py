"""The text remover's arithmetic: un-blending, a layer's colour, composing, and JPEG splicing."""

from pathlib import Path

import jpeglib
import numpy as np
from numpy.typing import NDArray
from PIL import Image

from detext import layers
from detext.judge import designed, verdicts
from detext.klein import crop_box
from detext.lama import TILE, starts
from detext.pipeline import Line, beside, keep_only

HEIGHT, WIDTH = 96, 128
type Colour = tuple[int, int, int]


def photo() -> NDArray[np.uint8]:
    """Return a smooth picture: gradients, so every region differs from its neighbours."""
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    red, green, blue = 40 + x, 60 + y, 120 + (x + y) / 4
    return np.asarray(np.clip(np.stack([red, green, blue], axis=2), 0, 255), dtype=np.uint8)


def plate(alpha: float) -> NDArray[np.float32]:
    """Return a translucent plate's opacity: a rectangle in the middle."""
    hard = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    hard[30:66, 30:98] = alpha
    return hard


def over(
    picture: NDArray[np.uint8], alpha: NDArray[np.float32], colour: Colour
) -> NDArray[np.uint8]:
    """Return a picture with a layer of `colour` at `alpha` drawn over it."""
    a = alpha[..., None]
    drawn = a * np.array(colour, dtype=np.float32) + (1 - a) * picture.astype(np.float32)
    return np.clip(np.rint(drawn), 0, 255).astype(np.uint8)


def test_unblend_brings_back_what_was_under_a_translucent_layer() -> None:
    """The photo under a half-opaque plate comes back exactly, given the plate's colour."""
    under = photo().astype(np.float32)
    alpha = plate(0.5)
    colour = np.array([20, 40, 60], dtype=np.float32)
    veiled = (alpha[..., None] * colour + (1 - alpha[..., None]) * under).astype(np.float32)
    back = layers.unblend(veiled, alpha, colour)
    assert np.abs(back - under).max() < 1e-3


def test_a_plates_colour_is_read_from_its_edge_without_trusting_the_fill() -> None:
    """A fill that guessed nothing right does not change the colour read off the edge."""
    alpha = plate(0.6)
    drawn = over(photo(), alpha, (200, 30, 90)).astype(np.float32)
    region = alpha > 0
    clear = ~layers.grow(region, 1)
    colour = layers.layer_colour(drawn, alpha, region, clear, np.zeros_like(drawn))
    assert np.abs(colour - np.array([200, 30, 90])).max() < 4


def test_compose_removes_a_translucent_plate_and_touches_nothing_else() -> None:
    """Under the plate, the photo; everywhere else, the very same pixels."""
    clean = photo()
    alpha = plate(0.6)
    drawn = over(clean, alpha, (0, 0, 0))
    result, changed = layers.compose(drawn, np.zeros_like(drawn), alpha, np.zeros_like(alpha))
    inside = alpha > 0
    assert np.abs(result.astype(int) - clean.astype(int))[inside].max() <= 3
    assert (result[~changed] == drawn[~changed]).all()
    assert not changed[~layers.grow(inside, layers.EDGE_PX + layers.RING_PX + 3)].any()


def test_opaque_overlay_takes_the_fill_matched_to_the_photos_level() -> None:
    """A fill with the right shapes but 12 levels dark is brought up to the photo around it."""
    clean = photo()
    alpha = plate(1.0)
    drawn = over(clean, alpha, (255, 255, 255))
    fill = np.clip(clean.astype(int) - 12, 0, 255).astype(np.uint8)
    result, _ = layers.compose(drawn, fill, alpha, np.zeros_like(alpha))
    middle = np.zeros_like(alpha, dtype=bool)
    middle[40:56, 45:83] = True
    assert np.abs(result.astype(int) - clean.astype(int))[middle].max() <= 3


def test_thin_translucent_strokes_go_to_the_fill_and_wide_plates_do_not() -> None:
    """A 3 px stroke would come back as its own ghost; a plate's inside comes back exactly."""
    mask = np.zeros((HEIGHT, WIDTH), dtype=bool)
    mask[10:13, 10:110] = True
    mask[30:70, 30:70] = True
    thin = layers.thin_parts(mask)
    assert thin[11, 50]
    assert not thin[50, 50]


def test_a_spliced_jpeg_keeps_every_block_the_edit_did_not_touch(tmp_path: Path) -> None:
    """Untouched blocks keep their coefficients, so no generation loss outside the edit."""
    original = tmp_path / "original.jpg"
    noise = np.random.default_rng(1).integers(-20, 20, (HEIGHT, WIDTH, 3))
    picture = np.clip(photo().astype(int) + noise, 0, 255).astype(np.uint8)
    Image.fromarray(picture).save(original, quality=85)
    decoded = np.asarray(Image.open(original).convert("RGB")).copy()
    changed = np.zeros((HEIGHT, WIDTH), dtype=bool)
    changed[40:50, 40:60] = True
    decoded[changed] = (255, 0, 0)
    target = tmp_path / "cleaned.jpg"
    layers.splice_jpeg(str(original), decoded, changed, str(target), str(tmp_path / "blocks.jpg"))
    before, after = jpeglib.read_dct(str(original)), jpeglib.read_dct(str(target))
    touched = layers.blocks_touched(changed, before.Y.shape, (1, 1))
    assert (before.Y[~touched] == after.Y[~touched]).all()
    assert not (before.Y[touched] == after.Y[touched]).all()
    far = ~layers.grow(changed, 24)
    shown_before = np.asarray(Image.open(original).convert("RGB"))
    shown_after = np.asarray(Image.open(target).convert("RGB"))
    assert (shown_before[far] == shown_after[far]).all()


def test_pieces_of_an_overlay_line_are_kept_and_pieces_elsewhere_are_not() -> None:
    """A caption's emoji goes with it; something the network liked across the picture stays."""
    hard = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    hard[20:30, 10:60] = 1.0
    hard[20:30, 64:70] = 1.0
    hard[80:90, 100:120] = 1.0
    line = Line(np.array([[10, 20], [60, 20], [60, 30], [10, 30]], dtype=np.int32), "caption")
    kept, _ = keep_only([line], [], hard, np.zeros_like(hard))
    assert kept[25, 30] == 1.0
    assert kept[25, 66] == 1.0
    assert kept[85, 110] == 0.0


def test_a_piece_touching_a_line_that_stays_is_left_whole() -> None:
    """A caption whose second line the checks did not agree on is not half taken off."""
    hard = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    hard[20:44, 10:60] = 1.0  # two lines of one caption, one piece
    first = Line(np.array([[10, 20], [60, 20], [60, 30], [10, 30]], dtype=np.int32), "golden hour")
    second = Line(np.array([[10, 34], [60, 34], [60, 44], [10, 44]], dtype=np.int32), "gets old")
    kept, _ = keep_only([first], [second], hard, np.zeros_like(hard))
    assert not kept.any()


def test_tiles_cover_a_long_patch_at_its_own_scale() -> None:
    """Every column of a 1500 px caption is in some 512 px tile, and no tile leaves the picture."""
    lefts = starts(100, 1500, 2000)
    covered = np.zeros(2000, dtype=bool)
    for left in lefts:
        covered[left : left + TILE] = True
    assert covered[100:1600].all()
    assert all(0 <= left <= 2000 - TILE for left in lefts)


def test_the_judges_reply_is_read_and_anything_unclear_is_scene() -> None:
    """Only a clear "added" removes a line."""
    assert verdicts('Sure: {"1": "added", "2": "scene"} done', 3) == [True, False, False]
    assert verdicts("I cannot tell", 2) == [False, False]
    assert verdicts('["added"]', 1) == [False]


def test_only_a_clear_no_lets_a_design_be_judged() -> None:
    """A book cover's own title is left alone; so is anything the design question leaves unclear."""
    assert not designed('{"design": false}')
    assert designed('{"design": true}')
    assert designed("a book cover, I think")


def test_a_crop_has_context_stays_inside_the_picture_and_is_big_enough() -> None:
    """A watermark in the corner gets a 512 px crop, slid back inside the picture."""
    left, top, right, bottom = crop_box((900, 10, 100, 40), (1080, 1350))
    assert 0 <= left <= 900
    assert 1000 <= right <= 1080
    assert right - left >= 512
    assert top == 0
    assert bottom >= 512


def test_lines_of_one_caption_are_beside_each_other_and_far_lines_are_not() -> None:
    """A meme's two top lines are one caption; a watermark in the corner is not part of it."""
    top = Line(np.array([[10, 10], [110, 10], [110, 30], [10, 30]], dtype=np.int32), "DAY 12")
    under = Line(np.array([[10, 34], [110, 34], [110, 54], [10, 54]], dtype=np.int32), "EVEREST")
    corner = Line(np.array([[90, 84], [126, 84], [126, 94], [90, 94]], dtype=np.int32), "@user")
    assert beside(top, under)
    assert not beside(top, corner)
