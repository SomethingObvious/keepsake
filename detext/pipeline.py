"""Find the text laid over a picture and take it off, leaving the text that belongs to the picture.

1. Every line of text is found (PP-OCRv6), scene text and overlay alike.
2. The overlay network marks, pixel by pixel, how opaque any added layer is:
    `hard` (glyphs, outlines, plates, stickers, icons) and `soft` (shadows and
    glows). It was trained to leave scene text at zero.
3. A line goes only when the network covers it and the judge, asked
    about every line, says it was added too: the network alone mistakes flat,
    sharp signage for stickers.
4. The picture is rebuilt without those lines' layers (see `layers`), and the
    lines are read again: an overlay that still reads is a failure, and so is
    a line of scene text that no longer reads the same.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Final, Protocol

import cv2
import numpy as np
import onnxruntime
from numpy.typing import NDArray
from PIL import Image as PILImage
from rapidocr import ModelType, OCRVersion, RapidOCR

from detext import layers
from detext.layers import Alpha, Mask

type Picture = NDArray[np.uint8]  # H x W x 3, RGB
type Quad = NDArray[np.int32]  # 4 x 2, x then y

# The network runs at up to this many pixels on the long side, in steps of 32.
NET_SIDE: Final = 1536
STRIDE: Final = 32
# The network's half of the vote: this much of a line's box covered by the
# hard layer. Overlays measured a median 0.44 (glyphs fill about a third of a
# box, a plate all of it), scene text a median 0 but up to 0.79 on flat
# signage, which is why the judge's half of the vote is not optional.
COVERED: Final = 0.12
# How far an overlay's pieces may sit from its line and still be part of it
# (an emoji after a caption, a logo before a watermark), in line heights.
REACH: Final = 0.6
# The band around a glyph painted with it, in line heights: a drop shadow's reach.
HALO: Final = 0.2
# Reading a scene line again: this similar, or it counts as changed.
SAME_TEXT: Final = 0.8
DETECT_SCORE: Final = 0.3


@dataclass(frozen=True, eq=False)  # one line is itself, not any line with equal numbers
class Line:
    """A line of text as the detector found it."""

    quad: Quad
    text: str

    def mask(self, shape: tuple[int, int]) -> Mask:
        """Return the line's box as a mask."""
        out = np.zeros(shape, dtype=np.uint8)
        cv2.fillPoly(out, [self.quad], 1)
        return out > 0

    @property
    def height(self) -> float:
        """Return the line's height in pixels."""
        return float(min(np.ptp(self.quad[:, 1]), np.ptp(self.quad[:, 0])))


@dataclass
class Outcome:
    """What happened to one picture."""

    removed: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    unsure: list[str] = field(default_factory=list)
    still_there: list[str] = field(default_factory=list)
    scene_changed: list[str] = field(default_factory=list)
    changed: Mask | None = None
    result: Picture | None = None


class Judge(Protocol):
    """Asks whether each line was added on top of the picture."""

    def __call__(self, picture: Picture, lines: Sequence[Line], /) -> list[bool]:
        """Return, for each line, whether it was added on top."""
        ...


type Fill = Callable[[Picture, Mask], Picture]


class Reader:
    """PP-OCRv6: every line of text in a picture."""

    def __init__(self, models: Path) -> None:
        """Load the medium detector and recogniser (ONNX, on the CPU)."""
        self.engine = RapidOCR(
            params={
                "Global.model_root_dir": str(models),
                "Global.log_level": "error",
                "Global.text_score": DETECT_SCORE,
                "Global.use_cls": False,
                "Det.ocr_version": OCRVersion.PPOCRV6,
                "Det.model_type": ModelType.MEDIUM,
                "Rec.ocr_version": OCRVersion.PPOCRV6,
                "Rec.model_type": ModelType.MEDIUM,
            }
        )

    def lines(self, picture: Picture) -> list[Line]:
        """Return every line of text, with what it says."""
        found = self.engine(np.ascontiguousarray(picture[:, :, ::-1]))
        boxes = np.zeros((0, 4, 2), dtype=np.float32) if found.boxes is None else found.boxes
        texts = list(found.txts or ())
        return [
            Line(np.asarray(box, dtype=np.float32).round().astype(np.int32), str(text))
            for box, text in zip(boxes, texts, strict=False)
        ]


class Overlay:
    """The overlay network: how opaque the added hard and soft layers are at each pixel."""

    def __init__(self, model: Path) -> None:
        """Load the network (ONNX, on the CPU)."""
        self.session = onnxruntime.InferenceSession(str(model), providers=["CPUExecutionProvider"])

    def alphas(self, picture: Picture) -> tuple[Alpha, Alpha]:
        """Return the hard and soft opacity maps, full size."""
        height, width = picture.shape[:2]
        scale = min(1.0, NET_SIDE / max(height, width))
        small = picture
        if scale < 1:
            size = (round(width * scale), round(height * scale))
            small = np.asarray(
                cv2.resize(picture, size, interpolation=cv2.INTER_AREA), dtype=np.uint8
            )
        tall, wide = small.shape[:2]
        padded = np.pad(
            small, ((0, -tall % STRIDE), (0, -wide % STRIDE), (0, 0)), mode="reflect"
        ).astype(np.float32)
        batch = (padded / np.float32(255)).transpose(2, 0, 1)[None]
        logits = self.session.run(None, {"image": batch})[0][0, :, :tall, :wide]
        maps = np.asarray(1 / (1 + np.exp(-logits)), dtype=np.float32)
        hard: Alpha = maps[0]
        soft: Alpha = maps[1]
        if scale < 1:
            hard = layers.floats(cv2.resize(hard, (width, height), interpolation=cv2.INTER_LINEAR))
            soft = layers.floats(cv2.resize(soft, (width, height), interpolation=cv2.INTER_LINEAR))
        return hard, soft


def coverage(line: Line, hard: Alpha) -> float:
    """Return how much of a line's box the hard layer covers."""
    inside = line.mask(hard.shape)
    return float(hard[inside].mean()) if inside.any() else 0.0


def keep_only(
    lines: Sequence[Line], staying: Sequence[Line], hard: Alpha, soft: Alpha
) -> tuple[Alpha, Alpha]:
    """Return the layers of the pieces that belong to these lines, and nothing else.

    A piece belongs to a line when it touches the line's box grown by part of
    the line's height: the caption's glyphs, its plate and shadow, and an emoji
    or logo beside it. A piece near no overlay line is left alone, whatever the
    network thought of it, and so is a piece that touches any line staying: a
    caption is never half taken off, and a line kept is never touched.
    """
    shape = hard.shape
    near = np.zeros(shape, dtype=bool)
    for line in lines:
        near |= layers.grow(line.mask(shape), max(2, round(REACH * line.height)))
    kept = np.zeros(shape, dtype=bool)
    for line in staying:
        kept |= line.mask(shape)
    pieces = layers.grow((hard > layers.HARD_FLOOR) | (soft > layers.SOFT_FLOOR), 1)
    count, found = cv2.connectedComponents(pieces.astype(np.uint8))
    labels = np.asarray(found, dtype=np.int32)
    wanted = np.zeros(count, dtype=bool)
    wanted[np.unique(labels[near & pieces])] = True
    wanted[np.unique(labels[kept & pieces])] = False
    wanted[0] = False
    keep = np.asarray(wanted[labels], dtype=bool)
    kept_hard = np.where(keep, hard, 0).astype(np.float32)
    return kept_hard, np.where(keep, soft, 0).astype(np.float32)


def beside(one: Line, other: Line) -> bool:
    """Return whether two lines sit close enough to be one caption (REACH of a line height)."""
    shape = (
        int(max(one.quad[:, 1].max(), other.quad[:, 1].max())) + 1,
        int(max(one.quad[:, 0].max(), other.quad[:, 0].max())) + 1,
    )
    reach = max(2, round(REACH * max(one.height, other.height)))
    return bool((layers.grow(one.mask(shape), reach) & other.mask(shape)).any())


def with_halo(hard: Alpha, lines: Sequence[Line], staying: Sequence[Line]) -> Alpha:
    """Return the hard layer with a halo around its glyphs counted as opaque too.

    The network sees glyphs better than their drop shadows and glows; a shadow
    it missed would stay behind as a dark ghost of the letters, so a band of a
    fifth of the line's height around each glyph is painted with them. Lines
    staying are never inside it.
    """
    if not lines:
        return hard
    margin = max(2, round(HALO * float(np.median([line.height for line in lines]))))
    band = layers.grow(hard >= layers.OPAQUE, margin)
    for line in staying:
        band &= ~line.mask(hard.shape)
    return np.maximum(hard, band.astype(np.float32))


def fill_mask(hard: Alpha, soft: Alpha) -> Mask:
    """Return the pixels a fill must paint: the opaque, and what un-blending cannot bring back."""
    parts = layers.zones(hard, soft)
    return (
        parts.fill
        | (parts.hard & layers.thin_parts(parts.hard))
        | (parts.hard & (hard >= layers.TRANSLUCENT))
        | (parts.soft & (soft >= layers.TRANSLUCENT))
    )


def similar(before: str, after: str) -> float:
    """Return how alike two readings of a line are, 0 to 1."""
    return SequenceMatcher(None, before, after).ratio()


def check(
    reader: Reader, result: Picture, gone: Sequence[Line], scene: Sequence[Line], outcome: Outcome
) -> None:
    """Read the result again: removed lines must not read, scene lines must read as before."""
    shape = result.shape[:2]
    again = reader.lines(result)
    for line in gone:
        box = line.mask(shape)
        if any((box & other.mask(shape)).sum() > box.sum() / 3 for other in again):
            outcome.still_there.append(line.text)
    for line in scene:
        box = line.mask(shape)
        if outcome.changed is None or not (box & outcome.changed).any():
            continue  # untouched, so certainly the same
        read = [o.text for o in again if (box & o.mask(shape)).sum() > box.sum() / 3]
        if not read or max(similar(line.text, text) for text in read) < SAME_TEXT:
            outcome.scene_changed.append(line.text)


def clean(
    picture: Picture,
    reader: Reader,
    overlay: Overlay,
    fill: Fill,
    judge: Judge | None = None,
) -> Outcome:
    """Return the picture without its overlay text, and an account of each line."""
    outcome = Outcome()
    lines = reader.lines(picture)
    if not lines:
        return outcome
    hard, soft = overlay.alphas(picture)
    net = [coverage(line, hard) >= COVERED for line in lines]
    asked = judge(picture, lines) if judge is not None and any(net) else net
    gone = [line for line, a, b in zip(lines, net, asked, strict=True) if a and b]
    scene = [line for line, a, b in zip(lines, net, asked, strict=True) if not a and not b]
    outcome.unsure = [line.text for line, a, b in zip(lines, net, asked, strict=True) if a != b]
    outcome.kept = [line.text for line in scene]
    if not gone:
        return outcome
    # A caption goes whole or not at all: a line beside one the checks disagreed on stays too.
    doubted = [line for line, a, b in zip(lines, net, asked, strict=True) if a and not b]
    held = [line for line in gone if any(beside(line, other) for other in doubted)]
    outcome.unsure += [line.text for line in held]
    gone = [line for line in gone if line not in held]
    staying = [line for line in lines if line not in gone]
    hard, soft = keep_only(gone, staying, hard, soft)
    taken = [line for line in gone if coverage(line, hard) >= COVERED]
    outcome.unsure += [line.text for line in gone if line not in taken]
    if not taken:
        return outcome
    hard = with_halo(hard, taken, staying)
    painted = fill(picture, fill_mask(hard, soft))
    result, changed = layers.compose(picture, painted, hard, soft)
    gone = taken
    outcome.removed = [line.text for line in gone]
    outcome.result, outcome.changed = result, changed
    check(reader, result, gone, scene, outcome)
    return outcome


def load(path: Path) -> Picture:
    """Return a picture's pixels as RGB, as they are stored (EXIF orientation is not applied).

    Stored orientation keeps JPEG blocks aligned for the splice. A sideways
    upload would need turning for detection and back again.
    """
    with PILImage.open(path) as image:
        return np.asarray(image.convert("RGB")).copy()
