"""Taking text off a picture by hand, the way a phone's magic eraser does.

The person paints over what should go. When a stroke ends, it snaps to what
in it is text: every colour unlike the ring just outside the stroke, and
whatever the overlay network sees laid on top, grown a little for the
anti-aliased edge, an outline or a shadow. Remove paints the marked pixels
over with MI-GAN, and can be pressed again on its own result. Saving writes a
copy beside the picture, a JPEG spliced so that every 8x8 block the edit did
not touch keeps its exact coefficients.

Everything here is numpy and Pillow, so the phone app can share it. ONNX
Runtime is imported on the thread that loads the models, as importing it takes
seconds, and jpeglib only when a JPEG is saved.
"""

import base64
import io
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw, JpegImagePlugin

from keepsake import media

type Picture = NDArray[np.uint8]  # H x W x 3, RGB
type Mask = NDArray[np.bool_]  # H x W
type Alpha = NDArray[np.float32]  # H x W, 0..1
type Box = tuple[slice, slice]  # rows, then columns
type Patch = dict[str, object]

# What can be written back without losing anything the edit did not change:
# JPEG block by block, PNG and WebP losslessly.
PICTURES: Final = frozenset({".jpg", ".jpeg", ".jfif", ".png", ".webp"})
JPEGS: Final = frozenset({".jpg", ".jpeg", ".jfif"})
OVERLAY: Final = "overlay.onnx"
MIGAN: Final = "migan.onnx"

# The overlay network reads pictures in steps of 32 px, at most this long a side:
# the whole picture for the first suggestion, and a stroke's surroundings to snap it.
STRIDE: Final = 32
SIDE: Final = 512
# Opacity from which the network's view of a pixel counts as laid on top.
SUGGESTED: Final = 0.5
SNAPPED: Final = 0.3
# The suggestion is grown by this share of the picture's long side, as a hand would paint it.
SUGGESTION_REACH: Final = 0.01
SUGGESTION_LEAST: Final = 4
# The snap: the ring outside a stroke gives the background's colours, in this
# many clusters, read from at most this many of its pixels. A pixel inside is
# text when it is further from every one of them than Otsu's threshold, and
# never nearer than FLOOR levels (two levels to one RGB unit).
COLOURS: Final = 8
ROUNDS: Final = 8
SAMPLE: Final = 3000
FLOOR: Final = 40
LEVELS_PER_UNIT: Final = 2
LEAST_RING: Final = 8
# How thick a stroke is, and the ring, gap closing and halo as shares of that.
THINNEST: Final = 4
# A stroke is snapped in a crop around it a quarter of its height bigger, and at least 6 px.
CROP_LEAST: Final = 6
RING_SHARE: Final = 5
CLOSE_SHARE: Final = 20
HALO_SHARE: Final = 16
# MI-GAN paints one patch at a time: holes in the same or a touching 16 px block are one patch,
# with a quarter of its size around it as context, and at least 64 px.
BLOCK: Final = 16
CONTEXT_SHARE: Final = 4
LEAST_CONTEXT: Final = 64
KNOWN: Final = 255
# The picture shown in the window: a JPEG of this quality is quick and indistinguishable.
SHOWN_QUALITY: Final = 92
# A JPEG's coefficient blocks.
DCT_BLOCK: Final = 8
# EXIF's orientation tag, and Pillow's turn from the stored pixels to the picture as
# shown for each value, as ImageOps.exif_transpose makes it; then the turn back.
ORIENTATION: Final = 0x0112
SHOWN: Final = {
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_270,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_90,
}
STORED: Final = {**SHOWN, 6: Image.Transpose.ROTATE_90, 8: Image.Transpose.ROTATE_270}


# --- masks ---


def grow(mask: Mask, radius: int) -> Mask:
    """Return a mask grown by `radius` pixels each way (a square), in time that ignores the radius.

    A pixel is on when any pixel within the square around it is: a running
    count along each axis, differenced across the square's width.
    """
    if radius < 1:
        return mask
    size = 2 * radius + 1
    for axis in (0, 1):
        width = [(0, 0), (0, 0)]
        width[axis] = (radius + 1, radius)
        sums = np.cumsum(np.pad(mask, width), axis=axis, dtype=np.int32)
        mask = sums[size:] > sums[:-size] if axis == 0 else sums[:, size:] > sums[:, :-size]
    return mask


def shrink(mask: Mask, radius: int) -> Mask:
    """Return a mask shrunk by `radius` pixels each way."""
    return ~grow(~mask, radius)


def bounds(mask: Mask, margin: int = 0) -> Box | None:
    """Return the box around a mask's pixels, grown by `margin` and kept inside it."""
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if not rows.size:
        return None
    height, width = mask.shape
    return (
        slice(max(0, int(rows[0]) - margin), min(height, int(rows[-1]) + 1 + margin)),
        slice(max(0, int(cols[0]) - margin), min(width, int(cols[-1]) + 1 + margin)),
    )


def brush(shape: tuple[int, int], points: list[tuple[float, float]], size: float) -> Mask:
    """Return a stroke of round brush `size` px across through `points`, as the window draws it."""
    image = Image.new("1", (shape[1], shape[0]))
    draw = ImageDraw.Draw(image)
    radius = size / 2
    if len(points) > 1:
        draw.line(points, fill=1, width=max(1, round(size)), joint="curve")
    for x, y in points:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=1)
    return np.asarray(image, dtype=bool)


# --- the snap ---


def otsu(levels: NDArray[np.uint8]) -> int:
    """Return Otsu's threshold: the level that best splits these values into two groups."""
    counts = np.bincount(levels, minlength=256).astype(np.float64)
    share = counts / max(1.0, float(counts.sum()))
    below = np.cumsum(share)
    mean = np.cumsum(share * np.arange(256))
    between = (mean[-1] * below - mean) ** 2 / np.maximum(below * (1 - below), 1e-12)
    return int(np.argmax(between))


def palette(colours: NDArray[np.float32]) -> NDArray[np.float32]:
    """Return a few colours that stand for these (k-means, the same every time)."""
    rng = np.random.default_rng(0)
    centres = colours[rng.choice(len(colours), min(COLOURS, len(colours)), replace=False)].copy()
    for _ in range(ROUNDS):
        nearest = distances(colours, centres).argmin(axis=1)
        for index in range(len(centres)):
            members = colours[nearest == index]
            if len(members):
                centres[index] = members.mean(axis=0)
    return centres


def distances(colours: NDArray[np.float32], centres: NDArray[np.float32]) -> NDArray[np.float32]:
    """Return each colour's distance to each centre, without an N x K x 3 array in between."""
    squared = (
        (colours**2).sum(axis=1)[:, None]
        - 2 * colours @ centres.T
        + (centres**2).sum(axis=1)[None, :]
    )
    return np.sqrt(np.maximum(squared, 0)).astype(np.float32)


def snap(picture: Picture, stroke: Mask, opacity: Alpha) -> Mask:
    """Return the part of a stroke that is text, given the picture and overlay around it.

    A person paints past the text, so the ring just outside a stroke is
    background: any colour inside the stroke unlike all of the ring's is text,
    and so is anything the overlay network sees laid on top. Small gaps close
    (a white letter inside a dark outline) and the result grows by a halo for
    the anti-aliased edge and a shadow, never past the stroke.
    """
    rows, cols = np.nonzero(stroke)
    if not rows.size:
        return stroke
    area = rows.size
    thick = max(THINNEST, min(area // np.unique(cols).size, area // np.unique(rows).size))
    ring = grow(stroke, max(3, thick // RING_SHARE)) & ~stroke
    outside = picture[ring].astype(np.float32)
    if len(outside) < LEAST_RING:
        return stroke
    if len(outside) > SAMPLE:
        outside = outside[np.random.default_rng(0).choice(len(outside), SAMPLE, replace=False)]
    far = distances(picture[stroke].astype(np.float32), palette(outside)).min(axis=1)
    levels = np.clip(far * LEVELS_PER_UNIT, 0, 255).astype(np.uint8)
    text = np.zeros(stroke.shape, dtype=bool)
    text[stroke] = levels > max(otsu(levels), FLOOR)
    text |= stroke & (opacity > SNAPPED)
    gap = max(1, thick // CLOSE_SHARE)
    text = shrink(grow(text, gap), gap)
    return grow(text, max(2, thick // HALO_SHARE)) & stroke


# --- the models ---


class Session(Protocol):
    """A loaded model: ONNX Runtime's InferenceSession, or anything that runs like one."""

    def run(
        self,
        output_names: Sequence[str] | None,
        input_feed: Mapping[str, NDArray[np.float32] | NDArray[np.uint8]],
        /,
    ) -> list[NDArray[np.float32] | NDArray[np.uint8]]:
        """Return the model's outputs for these inputs."""
        ...


class Models:
    """The overlay network and MI-GAN."""

    def __init__(self, overlay: Session, migan: Session) -> None:
        """Use these two loaded models."""
        self.overlay = overlay
        self.migan = migan

    def opacity(self, picture: Picture) -> Alpha:
        """Return how opaque anything laid over the picture is, read at most SIDE px a side."""
        return opacity(self.overlay, picture)

    def fill(self, picture: Picture, hole: Mask) -> Picture:
        """Return the picture with `hole` painted in and every other pixel as it was."""
        return fill(self.migan, picture, hole)


def load_models(folder: Path) -> Models:
    """Load both models on the processor; this is where ONNX Runtime is first imported."""
    import onnxruntime  # seconds to import, so only here, on the models' own thread

    options = onnxruntime.SessionOptions()
    options.log_severity_level = 3  # errors only: its warnings would fill the log
    cpu = ["CPUExecutionProvider"]
    return Models(
        onnxruntime.InferenceSession(str(folder / OVERLAY), options, providers=cpu),
        onnxruntime.InferenceSession(str(folder / MIGAN), options, providers=cpu),
    )


def opacity(session: Session, picture: Picture) -> Alpha:
    """Run the overlay network over a picture, and return its opacity map at full size.

    The network gives a hard layer (glyphs, outlines, plates) and a soft one
    (shadows and glows); either counts.
    """
    height, width = picture.shape[:2]
    scale = min(1.0, SIDE / max(height, width))
    tall = max(STRIDE, round(height * scale / STRIDE) * STRIDE)
    wide = max(STRIDE, round(width * scale / STRIDE) * STRIDE)
    small = Image.fromarray(picture).resize((wide, tall), Image.Resampling.BOX)
    batch = (np.asarray(small, dtype=np.float32) / np.float32(255)).transpose(2, 0, 1)[None]
    logits = np.asarray(session.run(None, {"image": batch})[0], dtype=np.float32)[0]
    alpha = (1 / (1 + np.exp(-logits.max(axis=0)))).astype(np.float32)
    full = Image.fromarray(alpha).resize((width, height), Image.Resampling.BILINEAR)
    return np.asarray(full, dtype=np.float32)


def suggestion(alpha: Alpha) -> Mask:
    """Return what looks laid on top of the whole picture, painted roughly, as a hand would."""
    reach = max(SUGGESTION_LEAST, round(SUGGESTION_REACH * max(alpha.shape)))
    return grow(alpha > SUGGESTED, reach)


def patches(hole: Mask) -> list[Box]:
    """Return the crops MI-GAN paints, one for each group of nearby holes, with context around it.

    Holes are gathered on a grid of 16 px blocks: each block with any hole,
    grown by one block, and the groups found by spreading the smallest block
    number through each until nothing changes.
    """
    height, width = hole.shape
    rows, cols = -(-height // BLOCK), -(-width // BLOCK)
    padded = np.zeros((rows * BLOCK, cols * BLOCK), dtype=bool)
    padded[:height, :width] = hole
    near = grow(padded.reshape(rows, BLOCK, cols, BLOCK).any(axis=(1, 3)), 1)
    none = near.size
    labels = np.where(near, np.arange(none).reshape(near.shape), none)
    while True:
        spread = labels.copy()
        np.minimum(spread[1:], labels[:-1], out=spread[1:])
        np.minimum(spread[:-1], labels[1:], out=spread[:-1])
        np.minimum(spread[:, 1:], labels[:, :-1], out=spread[:, 1:])
        np.minimum(spread[:, :-1], labels[:, 1:], out=spread[:, :-1])
        spread[~near] = none
        if (spread == labels).all():
            break
        labels = spread
    crops: list[Box] = []
    for label in np.unique(labels[near]):
        cells = bounds(labels == label)
        if cells is None:
            continue
        top, left = cells[0].start * BLOCK, cells[1].start * BLOCK
        box = bounds(hole[top : cells[0].stop * BLOCK, left : cells[1].stop * BLOCK])
        if box is None:
            continue
        y0, y1 = top + box[0].start, top + box[0].stop
        x0, x1 = left + box[1].start, left + box[1].stop
        reach = max(LEAST_CONTEXT, max(y1 - y0, x1 - x0) // CONTEXT_SHARE)
        crops.append(
            (
                slice(max(0, y0 - reach), min(height, y1 + reach)),
                slice(max(0, x0 - reach), min(width, x1 + reach)),
            )
        )
    return crops


def fill(session: Session, picture: Picture, hole: Mask) -> Picture:
    """Paint each patch of `hole` with MI-GAN, which crops and scales to its 512 px itself."""
    out = picture.copy()
    for box in patches(hole):
        crop, here = out[box], hole[box]
        image = np.ascontiguousarray(crop.transpose(2, 0, 1)[None])
        mask = np.where(here, 0, KNOWN).astype(np.uint8)[None, None]
        painted = np.asarray(session.run(None, {"image": image, "mask": mask})[0], dtype=np.uint8)
        crop[here] = painted[0].transpose(1, 2, 0)[here]
    return out


# --- reading and writing pictures ---


@dataclass
class Opened:
    """A picture as the person sees it, and what saving it needs to keep."""

    path: Path
    picture: Picture  # turned upright by its EXIF orientation
    orientation: int
    alpha: NDArray[np.uint8] | None  # PNG and WebP transparency, upright too
    icc: bytes | None


def load(path: Path) -> Opened:
    """Return a picture's pixels the way they are shown: turned by its EXIF orientation."""
    with Image.open(path) as image:
        orientation = int(image.getexif().get(ORIENTATION, 1))
        icc = image.info.get("icc_profile")
        turn = SHOWN.get(orientation)
        upright = image.transpose(turn) if turn is not None else image
        alpha = (
            np.asarray(upright.convert("RGBA"))[..., 3].copy()
            if "A" in upright.getbands() or "transparency" in image.info
            else None
        )
        picture = np.asarray(upright.convert("RGB")).copy()
    return Opened(path, picture, orientation, alpha, icc if isinstance(icc, bytes) else None)


def stored(array: NDArray[np.uint8], orientation: int) -> NDArray[np.uint8]:
    """Return upright pixels turned back the way the file stores them."""
    turn = STORED.get(orientation)
    return array if turn is None else np.asarray(Image.fromarray(array).transpose(turn))


def blocks_touched(mask: Mask, grid: tuple[int, ...], scale: tuple[int, int]) -> NDArray[np.bool_]:
    """Return which blocks of a JPEG component's grid hold any of `mask`.

    Each block covers 8 px times the component's subsampling (`scale`, down
    and across) of the full picture.
    """
    rows, cols = grid[0], grid[1]
    tall, wide = DCT_BLOCK * scale[0], DCT_BLOCK * scale[1]
    padded = np.zeros((rows * tall, cols * wide), dtype=bool)
    height, width = min(mask.shape[0], rows * tall), min(mask.shape[1], cols * wide)
    padded[:height, :width] = mask[:height, :width]
    return padded.reshape(rows, tall, cols, wide).any(axis=(1, 3))


def splice_jpeg(
    original: Path, edited: Picture, changed: Mask, target: Path, scratch: Path
) -> None:
    """Write `edited` as a JPEG that keeps every 8x8 block of `original` the edit did not touch.

    The touched blocks are encoded with the original's own quantisation tables
    and chroma sampling, so they match their neighbours; every other block's
    coefficients are copied, which means no generation loss outside the edit,
    and the original's EXIF and colour profile stay. Without jpeglib, as in
    the phone app, the whole picture is encoded again instead.
    """
    try:
        import jpeglib  # only a JPEG needs it
    except ImportError:
        encode_jpeg(original, edited, target)
        return
    source = jpeglib.read_dct(str(original))
    fresh = jpeglib.from_spatial(np.ascontiguousarray(edited))
    fresh.samp_factor = source.samp_factor
    fresh.write_spatial(str(scratch), qt=source.qt, quant_tbl_no=source.quant_tbl_no)
    redone = jpeglib.read_dct(str(scratch))
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
    source.write_dct(str(target))


def encode_jpeg(original: Path, edited: Picture, target: Path) -> None:
    """Write `edited` as a new JPEG with the original's tables, sampling, EXIF and colour profile.

    Every block is encoded again, so unlike the splice nothing promises that
    the rest of the picture stays exactly as it was, though with the
    original's own tables it barely moves.
    """
    with Image.open(original) as source:
        settings: dict[str, object] = {
            "exif": source.info.get("exif", b""),
            "icc_profile": source.info.get("icc_profile"),
        }
        if isinstance(source, JpegImagePlugin.JpegImageFile):
            settings["qtables"] = source.quantization
            settings["subsampling"] = JpegImagePlugin.get_sampling(source)
    Image.fromarray(edited).save(target, "JPEG", **settings)


def keep_beside(original: Path, cleaned: Path) -> Path:
    """Give the cleaned picture a name of its own beside the original, which stays as it was.

    Saving makes a copy, the way Save Frame and Save Clip do, so nothing
    anyone kept is changed.
    """
    target = media.beside(original, "no text", original.suffix)
    cleaned.replace(target)
    return target


def write(opened: Opened, picture: Picture, changed: Mask) -> Path:
    """Save the edited picture beside the original, changing nothing the edit did not."""
    path = opened.path
    cleaned = path.with_name(f"{path.stem}.cleaned{path.suffix}")
    try:
        if path.suffix.lower() in JPEGS:
            scratch = path.with_name(f"{path.stem}.blocks.jpg")
            try:
                splice_jpeg(
                    path,
                    stored(picture, opened.orientation),
                    stored(changed.astype(np.uint8), opened.orientation) > 0,
                    cleaned,
                    scratch,
                )
            finally:
                scratch.unlink(missing_ok=True)
        else:
            image = Image.fromarray(picture)
            if opened.alpha is not None:
                image.putalpha(Image.fromarray(opened.alpha))
            extra: dict[str, object] = {"icc_profile": opened.icc} if opened.icc else {}
            if path.suffix.lower() == ".webp":
                image.save(cleaned, "WEBP", lossless=True, exact=True, **extra)
            else:
                image.save(cleaned, "PNG", optimize=True, **extra)
        return keep_beside(path, cleaned)
    finally:
        cleaned.unlink(missing_ok=True)


def data_url(image: Image.Image, kind: str, **settings: object) -> str:
    """Return an image as a data: address the window can draw without reading any file."""
    buffer = io.BytesIO()
    image.save(buffer, kind, **settings)
    return f"data:image/{kind.lower()};base64,{base64.b64encode(buffer.getvalue()).decode()}"


# --- the editor ---


@dataclass
class Step:
    """What one edit changed, kept so that Undo can put it back."""

    box: Box
    mask: Mask
    picture: Picture | None = None


class Editor:
    """The picture open in the eraser: its pixels, the marked part, and every step to undo.

    One picture at a time. The models load once, on a thread of their own, the
    first time a picture opens; anything that needs them waits for that. A lock
    keeps edits in order, though the window sends them one at a time anyway.
    """

    def __init__(self) -> None:
        """Start with nothing open and nothing loaded."""
        self.lock = threading.Lock()
        self.loading: threading.Thread | None = None
        self.models: Models | None = None
        self.problem = ""
        self.opened: Opened | None = None
        self.picture: Picture = np.zeros((0, 0, 3), dtype=np.uint8)
        self.mask: Mask = np.zeros((0, 0), dtype=bool)
        self.steps: list[Step] = []

    def load_models(self, folder: Path) -> None:
        """Start loading the models, unless they are loaded or loading."""
        if self.models is None and (self.loading is None or not self.loading.is_alive()):
            self.loading = threading.Thread(
                target=self.loader, args=(folder,), daemon=True, name="eraser"
            )
            self.loading.start()

    def loader(self, folder: Path) -> None:
        """Load the models, or remember why they would not load."""
        try:
            self.models = load_models(folder)
            self.problem = ""
        except (ImportError, OSError, RuntimeError, ValueError) as problem:
            self.problem = (
                f"The eraser's models would not load ({problem}). Set it up again in Settings."
            )

    def ready(self) -> Models:
        """Return the models once loaded, or raise RuntimeError saying why they would not load."""
        if self.loading is not None:
            self.loading.join()
        if self.models is None:
            raise RuntimeError(self.problem or "The eraser has not been set up")
        return self.models

    def open(self, path: Path, folder: Path) -> dict[str, object]:
        """Open a picture, start the models loading, and return what the window draws."""
        self.load_models(folder)
        try:
            opened = load(path)
        except (OSError, ValueError, Image.DecompressionBombError) as problem:
            message = "That picture could not be opened"
            raise RuntimeError(message) from problem
        with self.lock:
            self.opened = opened
            self.picture = opened.picture.copy()
            self.mask = np.zeros(self.picture.shape[:2], dtype=bool)
            self.steps = []
            height, width = self.picture.shape[:2]
            shown = Image.fromarray(self.picture)
            return {
                "width": width,
                "height": height,
                "picture": data_url(shown, "JPEG", quality=SHOWN_QUALITY),
            }

    def close(self) -> None:
        """Let the picture go; the models stay loaded for the next one."""
        with self.lock:
            self.opened = None
            self.picture = np.zeros((0, 0, 3), dtype=np.uint8)
            self.mask = np.zeros((0, 0), dtype=bool)
            self.steps = []

    def suggest(self) -> Patch | None:
        """Mark what the overlay network sees laid on top of the whole picture, as a first guess."""
        models = self.ready()
        with self.lock:
            if self.opened is None:
                return None
            found = suggestion(models.opacity(self.picture))
            box = bounds(found)
            if box is None:
                return None
            self.steps.append(Step(box, self.mask[box].copy()))
            self.mask[box] |= found[box]
            return self.patch(box, picture=False)

    def stroke(
        self, points: list[tuple[float, float]], size: float, *, erase: bool, snapped: bool
    ) -> Patch | None:
        """Add a stroke to the marked part (snapped to the text in it, if asked) or take it away."""
        models = self.ready() if snapped and not erase else None
        with self.lock:
            if self.opened is None or not points:
                return None
            height, width = self.mask.shape
            xs, ys = [x for x, _ in points], [y for _, y in points]
            # Room for the ring outside the stroke, and context for the network.
            reach = round(size / 2) + max(CROP_LEAST, round(max(ys) - min(ys) + size) // 4)
            box = (
                slice(max(0, int(min(ys)) - reach), min(height, int(max(ys)) + reach + 1)),
                slice(max(0, int(min(xs)) - reach), min(width, int(max(xs)) + reach + 1)),
            )
            if box[0].start >= box[0].stop or box[1].start >= box[1].stop:
                return None
            here = [(x - box[1].start, y - box[0].start) for x, y in points]
            drawn = brush((box[0].stop - box[0].start, box[1].stop - box[1].start), here, size)
            if models is not None:
                crop = self.picture[box]
                drawn = snap(crop, drawn, models.opacity(crop))
            self.steps.append(Step(box, self.mask[box].copy()))
            if erase:
                self.mask[box] &= ~drawn
            else:
                self.mask[box] |= drawn
            return self.patch(box, picture=False)

    def remove(self) -> Patch | None:
        """Paint over everything marked, and clear the mark."""
        models = self.ready()
        with self.lock:
            box = bounds(self.mask)
            if self.opened is None or box is None:
                return None
            painted = models.fill(self.picture, self.mask)
            self.steps.append(Step(box, self.mask[box].copy(), self.picture[box].copy()))
            self.picture[box] = painted[box]
            self.mask[box] = False
            return self.patch(box, picture=True)

    def undo(self) -> Patch | None:
        """Take back the last stroke, suggestion or removal."""
        with self.lock:
            if not self.steps:
                return None
            step = self.steps.pop()
            self.mask[step.box] = step.mask
            if step.picture is not None:
                self.picture[step.box] = step.picture
            return self.patch(step.box, picture=step.picture is not None)

    def save(self) -> Path | None:
        """Write the edited picture beside the original; None when nothing has changed."""
        with self.lock:
            if self.opened is None:
                return None
            changed = (self.picture != self.opened.picture).any(axis=2)
            if not changed.any():
                return None
            try:
                return write(self.opened, self.picture, changed)
            except (OSError, ValueError) as problem:
                message = f"The copy could not be saved: {problem}"
                raise RuntimeError(message) from problem

    def patch(self, box: Box, *, picture: bool) -> Patch:
        """Return one rectangle of the marked part (and of the picture) for the window to redraw."""
        marked = self.mask[box].astype(np.uint8) * np.uint8(255)
        shade = np.full(marked.shape, 255, dtype=np.uint8)
        found: Patch = {
            "x": box[1].start,
            "y": box[0].start,
            "w": box[1].stop - box[1].start,
            "h": box[0].stop - box[0].start,
            "mask": data_url(Image.fromarray(np.dstack([shade, marked])), "PNG"),
        }
        if picture:
            found["picture"] = data_url(
                Image.fromarray(self.picture[box]), "JPEG", quality=SHOWN_QUALITY
            )
        return found
