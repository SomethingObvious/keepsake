"""The quick tier's fill: LaMa (ONNX, 512 x 512), over the picture at its own resolution, in tiles.

Each patch to paint is covered by 512 px tiles at native scale, three quarters
of a tile apart. A tile sees what earlier tiles already painted, so a long
caption fills from one end to the other without a seam, and nothing is
shrunk to fit and blurred on the way back.
"""

from pathlib import Path
from typing import Final

import cv2
import numpy as np
import onnxruntime
from numpy.typing import NDArray

from detext.layers import Mask

TILE: Final = 512
MARGIN: Final = 32  # context kept around a patch inside its tile
GATHER: Final = 31  # patches this close are painted as one
BYTE: Final = 255


class Lama:
    """LaMa inpainting, on the CPU."""

    def __init__(self, model: Path) -> None:
        """Load the model."""
        self.session = onnxruntime.InferenceSession(str(model), providers=["CPUExecutionProvider"])

    def tile(self, picture: NDArray[np.uint8], hole: Mask) -> NDArray[np.uint8]:
        """Paint one 512 x 512 tile."""
        image = (picture.astype(np.float32) / np.float32(BYTE)).transpose(2, 0, 1)[None]
        mask = hole.astype(np.float32)[None, None]
        painted = self.session.run(None, {"image": image, "mask": mask})[0][0].transpose(1, 2, 0)
        return np.asarray(np.clip(painted, 0, BYTE), dtype=np.uint8)

    def __call__(self, picture: NDArray[np.uint8], hole: Mask) -> NDArray[np.uint8]:
        """Return the picture with `hole` painted in; everything else as it was."""
        height, width = hole.shape
        pad = ((0, max(0, TILE - height)), (0, max(0, TILE - width)))
        work = np.pad(picture, (*pad, (0, 0)), mode="reflect")
        todo = np.pad(hole, pad)
        patches = cv2.dilate(todo.astype(np.uint8), np.ones((GATHER, GATHER), np.uint8))
        count, _, stats, _ = cv2.connectedComponentsWithStats(patches)
        for index in range(1, count):
            x, y, w, h = (int(v) for v in stats[index, :4])
            for top in starts(y, h, work.shape[0]):
                for left in starts(x, w, work.shape[1]):
                    here = todo[top : top + TILE, left : left + TILE]
                    if not here.any():
                        continue
                    painted = self.tile(work[top : top + TILE, left : left + TILE], here)
                    work[top : top + TILE, left : left + TILE][here] = painted[here]
                    here[:] = False
        return work[:height, :width]


def starts(at: int, size: int, limit: int) -> list[int]:
    """Return where tiles along one axis begin, to cover `size` px from `at` with context."""
    if size <= TILE - 2 * MARGIN:
        first = [at + size // 2 - TILE // 2]
    else:
        first = [
            *range(at - MARGIN, at + size - TILE + 2 * MARGIN, 3 * TILE // 4),
            at + size + MARGIN - TILE,
        ]
    return sorted({min(max(0, v), limit - TILE) for v in first})
