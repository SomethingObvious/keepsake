from collections.abc import Mapping
from enum import Enum

import numpy as np
from numpy.typing import NDArray

class OCRVersion(Enum):
    PPOCRV4 = "PP-OCRv4"
    PPOCRV5 = "PP-OCRv5"
    PPOCRV6 = "PP-OCRv6"

class ModelType(Enum):
    MOBILE = "mobile"
    SERVER = "server"
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"

class RapidOCROutput:
    boxes: NDArray[np.float32] | None
    txts: tuple[str, ...] | None

class RapidOCR:
    def __init__(
        self, config_path: str | None = ..., params: Mapping[str, object] | None = ...
    ) -> None: ...
    def __call__(self, img_content: NDArray[np.uint8]) -> RapidOCROutput: ...
