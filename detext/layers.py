"""Putting a picture back together without its overlay, one kind of overlay pixel at a time.

An overlay is two layers over the photo, each with an opacity in 0..1:

* hard: glyphs, outlines, plates, stickers, icons. Where it is opaque, the
    photo under it is gone and has to be filled in.
* soft: shadows and glows, drawn under the hard layer.

Wherever either is translucent, the photo is still there, only veiled:
`pixel = alpha * colour + (1 - alpha) * photo`. Solving that for the photo
brings back what was under a see-through plate, a faint watermark or a
shadow exactly as it was, where a fill would only invent something like it.
"""

from dataclasses import dataclass
from typing import Final

import cv2
import jpeglib
import numpy as np
from numpy.typing import NDArray

type Image = NDArray[np.float32]  # H x W x 3, 0..255
type Alpha = NDArray[np.float32]  # H x W, 0..1
type Mask = NDArray[np.bool_]  # H x W

# Opacity from which the photo under a pixel is taken as lost; from TRANSLUCENT
# up to it, the fill and the un-blend are mixed, since dividing by 1 - alpha
# multiplies the JPEG noise by 1 / (1 - alpha): four times at 0.75.
OPAQUE: Final = 0.9
TRANSLUCENT: Final = 0.6
# Below these a layer is not there at all (2/255 and 3/255).
HARD_FLOOR: Final = 0.012
SOFT_FLOOR: Final = 0.008
# Glyph edges are a 1 px opacity ramp to the glyph's own colour; they belong
# with the opaque glyph, not with a plate's colour.
EDGE_PX: Final = 2
# JPEG rings a few pixels past a sharp edge: the fill covers that much more.
RING_PX: Final = 3
# How far outside an overlay the photo is read to learn the overlay's colour,
# and the least opacity a pixel needs to say anything about that colour: at
# 0.02 a one-level error in the photo is a fifty-level error in the colour.
NEAR_PX: Final = 6
TELLING: Final = 0.08
MIN_PAIRS: Final = 30
MAD_SCALE: Final = 1.4826
OUTLIER_MADS: Final = 3.0
BLOCK: Final = 8
# A translucent piece no deeper than this from its edge to its middle is a stroke.
THIN_PX: Final = 4.0
# The scales an offset field is read at, finest first, and how much pinned
# weight a pixel needs at a scale to trust it there.
SCALES: Final = (3.0, 9.0, 27.0)
ENOUGH: Final = 0.08


@dataclass(frozen=True)
class Zones:
    """Which treatment each pixel of an overlay gets."""

    fill: Mask  # opaque: replaced by the fill
    hard: Mask  # translucent hard layer: un-blended
    soft: Mask  # shadow or glow: un-blended

    @property
    def changed(self) -> Mask:
        """Every pixel the result may differ in."""
        return self.fill | self.hard | self.soft


def floats(value: object) -> NDArray[np.float32]:
    """Return what OpenCV handed back as a float32 array (its own type is looser than numpy's)."""
    return np.asarray(value, dtype=np.float32)


def disc(radius: int) -> NDArray[np.uint8]:
    """Return a round structuring element."""
    shape = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    return np.asarray(shape, dtype=np.uint8)


def grow(mask: Mask, radius: int) -> Mask:
    """Return a mask grown by `radius` pixels."""
    return cv2.dilate(mask.astype(np.uint8), disc(radius)) > 0


def zones(hard: Alpha, soft: Alpha) -> Zones:
    """Split an overlay's footprint by treatment."""
    # A glow is often solid right beside its letters: opaque is opaque, whichever layer.
    opaque = grow((hard >= OPAQUE) | (soft >= OPAQUE), EDGE_PX)
    fill = grow(opaque, RING_PX)
    translucent = (hard > HARD_FLOOR) & ~fill
    veiled = (soft > SOFT_FLOOR) & ~fill & ~translucent
    return Zones(fill=fill, hard=translucent, soft=veiled)


def nearby(image: Image, where: Mask, sigma: float) -> Image:
    """Return, at each pixel, the average colour of the `where` pixels around it."""
    weight = where.astype(np.float32)
    total = cv2.GaussianBlur(image * weight[..., None], (0, 0), sigma)
    count = cv2.GaussianBlur(weight, (0, 0), sigma)[..., None]
    return (total / np.maximum(count, 1e-4)).astype(np.float32)


def robust_median(values: NDArray[np.float32]) -> NDArray[np.float32]:
    """Return the per-channel median of rows, after dropping rows more than 3 MADs out."""
    middle = np.median(values, axis=0)
    spread = np.median(np.abs(values - middle), axis=0) * MAD_SCALE + 1.0
    kept = values[(np.abs(values - middle) <= OUTLIER_MADS * spread).all(axis=1)]
    return np.asarray(
        np.median(kept if len(kept) >= MIN_PAIRS else values, axis=0), dtype=np.float32
    )


def layer_colour(
    image: Image, alpha: Alpha, region: Mask, clear: Mask, fill: Image
) -> NDArray[np.float32]:
    """Return the colour a translucent layer was drawn in, from pixels just inside its edge.

    The photo a few pixels inside the edge is close to the photo a few pixels
    outside it, where nothing covers it, so `pixel = a*colour + (1-a)*outside`
    gives the colour without trusting any fill. With too few such pixels (a
    watermark's thin strokes), the fill stands in for the photo instead.
    """
    outside = nearby(image, clear, NEAR_PX)
    rim = region & grow(clear, 2 * NEAR_PX) & (alpha >= TELLING)
    under = outside
    if int(rim.sum()) < MIN_PAIRS:
        rim, under = region & (alpha >= TELLING), fill
    if not rim.any():
        return robust_median(image[region])
    a = alpha[rim][:, None]
    guesses = ((image[rim] - (1 - a) * under[rim]) / a).astype(np.float32)
    # Each guess weighs by its opacity squared: the least-squares colour.
    middle = np.median(guesses, axis=0)
    spread = np.median(np.abs(guesses - middle), axis=0) * MAD_SCALE + 1.0
    kept = (np.abs(guesses - middle) <= OUTLIER_MADS * spread).all(axis=1)
    weight = (a[:, 0] ** 2) * kept
    colour = (guesses * weight[:, None]).sum(axis=0) / max(float(weight.sum()), 1e-6)
    return np.asarray(np.clip(colour, 0, 255), dtype=np.float32)


def unblend(image: Image, alpha: Alpha, colour: NDArray[np.float32]) -> Image:
    """Return the photo under a layer of `colour` at `alpha`."""
    a = np.minimum(alpha, OPAQUE)[..., None]
    return np.asarray((image - a * colour) / (1 - a), dtype=np.float32)


def shift_onto(known: Image, fill: Image, region: Mask, usable: Mask) -> Image:
    """Return the fill moved onto the known photo's level around `region`, smoothly and robustly.

    The offset `known - fill` is read in a ring around the region and spread
    in by normalised convolution, finest scale first, so a fill that came out
    a little dark in one corner is lifted there and not elsewhere. Offsets
    more than 3 MADs from the ring's median are dropped: near an overlay a
    fill often draws different content (a bigger ear, another cloud), and that
    change of shape must not be read as a change of colour.
    """
    ring = grow(region, 4 * NEAR_PX) & usable & ~region
    if int(ring.sum()) < MIN_PAIRS:
        return fill
    offset = (known - fill).astype(np.float32)
    middle = np.median(offset[ring], axis=0)
    spread = np.median(np.abs(offset[ring] - middle), axis=0) * MAD_SCALE + 1.0
    pins = ring & (np.abs(offset - middle) <= OUTLIER_MADS * spread).all(axis=2)
    field = np.broadcast_to(middle, offset.shape).astype(np.float32).copy()
    settled = np.zeros(region.shape, dtype=bool)
    for sigma in SCALES:
        total = cv2.GaussianBlur(offset * pins[..., None], (0, 0), sigma)
        weight = cv2.GaussianBlur(pins.astype(np.float32), (0, 0), sigma)
        here = (weight > ENOUGH) & ~settled
        field[here] = (total / np.maximum(weight, 1e-6)[..., None])[here]
        settled |= here
    return np.asarray(fill + field, dtype=np.float32)


def toward_fill(alpha: Alpha) -> Alpha:
    """Return how much fill to mix into an un-blend: none up to TRANSLUCENT, all at OPAQUE."""
    return np.asarray(
        np.clip((alpha - TRANSLUCENT) / (OPAQUE - TRANSLUCENT), 0, 1), dtype=np.float32
    )


def thin_parts(layer: Mask) -> Mask:
    """Return the pieces of a translucent layer too thin to un-blend, such as a watermark's strokes.

    Un-blending divides JPEG's error by 1 - alpha, and that error gathers at
    sharp edges: a stroke a few pixels wide is all edge and would come back as
    its own ghost, so it goes to the fill. A plate is wide, and its inside
    comes back exactly.
    """
    count, found = cv2.connectedComponents(layer.astype(np.uint8))
    labels = np.asarray(found, dtype=np.int32)
    depth = np.asarray(
        cv2.distanceTransform(layer.astype(np.uint8), cv2.DIST_L2, 3), dtype=np.float32
    )
    deepest = np.zeros(count, dtype=np.float32)
    np.maximum.at(deepest, labels.ravel(), depth.ravel())
    thin = deepest < THIN_PX
    thin[0] = False
    return np.asarray(thin[labels], dtype=bool)


def compose(
    photo: NDArray[np.uint8], fill: NDArray[np.uint8], hard: Alpha, soft: Alpha
) -> tuple[NDArray[np.uint8], Mask]:
    """Return the photo without the overlay described by `hard` and `soft`, and what changed.

    `fill` is a picture of the same size with the opaque parts painted over,
    by LaMa or by FLUX.2 Klein; only its pixels under opaque overlay are used,
    and its colour guesses where un-blending needs one.
    """
    image = photo.astype(np.float32)
    guess = fill.astype(np.float32)
    parts = zones(hard, soft)
    touched = parts.changed
    clear = ~grow(touched, 1)
    out = image.copy()
    count, found = cv2.connectedComponents(grow(touched, EDGE_PX).astype(np.uint8))
    labels = np.asarray(found, dtype=np.int32)
    for index in range(1, count):
        region = np.equal(labels, index)
        # Undo the hard layer, then the soft one under it, then fill what is lost;
        # where un-blending would amplify noise too far, the fill takes over.
        layer = region & parts.hard
        veil = region & (parts.soft | (parts.hard & (soft > SOFT_FLOOR)))
        lost = region & parts.fill
        under = image.copy()
        trusted = clear.copy()
        if layer.any():
            colour = layer_colour(image, hard, layer, clear, guess)
            mix = np.maximum(toward_fill(hard), thin_parts(layer).astype(np.float32))
            recovered = unblend(image, hard, colour)
            sure = layer & (mix == 0)
            under[sure] = recovered[sure]
            trusted |= sure
            rough = shift_onto(under, guess, layer & ~sure, trusted)
            m = mix[..., None]
            under[layer] = (recovered * (1 - m) + rough * m)[layer]
        if veil.any():
            colour = layer_colour(under, soft, veil, clear, guess)
            mix = toward_fill(soft)
            recovered = unblend(under, soft, colour)
            sure = veil & (mix == 0)
            under[sure] = recovered[sure]
            trusted |= sure
            rough = shift_onto(under, guess, veil & ~sure, trusted)
            m = mix[..., None]
            under[veil] = (recovered * (1 - m) + rough * m)[veil]
        if lost.any():
            # Matched to what is now known right around it: the photo, or the photo recovered.
            placed = shift_onto(under, guess, lost, (trusted | layer | veil) & ~lost)
            blurred = floats(cv2.GaussianBlur(lost.astype(np.float32), (0, 0), 1.0))
            edge = np.maximum(blurred, lost.astype(np.float32))
            under = under * (1 - edge[..., None]) + placed * edge[..., None]
        out[region] = under[region]
    result = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return result, (result != photo).any(axis=2)


def blocks_touched(mask: Mask, grid: tuple[int, ...], scale: tuple[int, int]) -> NDArray[np.bool_]:
    """Return which blocks of a JPEG component's grid hold any of `mask`.

    Each block covers 8 px times the component's subsampling (`scale`, down
    and across) of the full picture.
    """
    rows, cols = grid[0], grid[1]
    tall, wide = BLOCK * scale[0], BLOCK * scale[1]
    padded = np.zeros((rows * tall, cols * wide), dtype=bool)
    height, width = min(mask.shape[0], rows * tall), min(mask.shape[1], cols * wide)
    padded[:height, :width] = mask[:height, :width]
    return padded.reshape(rows, tall, cols, wide).any(axis=(1, 3))


def splice_jpeg(
    original: str, edited: NDArray[np.uint8], changed: Mask, target: str, scratch: str
) -> None:
    """Write `edited` as a JPEG that keeps every 8x8 block of `original` the edit did not touch.

    The touched blocks are encoded with the original's own quantisation tables
    and chroma sampling, so they match their neighbours; every other block's
    coefficients are copied, which means no generation loss outside the edit.
    """
    source = jpeglib.read_dct(original)
    fresh = jpeglib.from_spatial(np.ascontiguousarray(edited))
    fresh.samp_factor = source.samp_factor
    fresh.write_spatial(scratch, qt=source.qt, quant_tbl_no=source.quant_tbl_no)
    redone = jpeglib.read_dct(scratch)
    luma = blocks_touched(changed, source.Y.shape, (1, 1))
    source.Y[luma] = redone.Y[luma]
    if (
        source.Cb is not None
        and source.Cr is not None
        and redone.Cb is not None
        and redone.Cr is not None
    ):
        # The subsampling, read off the grids: a 4:2:0 chroma block covers 16 x 16 px.
        scale = (
            round(source.Y.shape[0] / source.Cb.shape[0]),
            round(source.Y.shape[1] / source.Cb.shape[1]),
        )
        chroma = blocks_touched(changed, source.Cb.shape, scale)
        source.Cb[chroma] = redone.Cb[chroma]
        source.Cr[chroma] = redone.Cr[chroma]
    source.write_dct(target)
