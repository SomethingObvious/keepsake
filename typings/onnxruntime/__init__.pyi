from collections.abc import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

class SessionOptions:
    log_severity_level: int
    def __init__(self) -> None: ...

class InferenceSession:
    def __init__(
        self,
        path_or_bytes: str,
        sess_options: SessionOptions | None = ...,
        providers: Sequence[str] | None = ...,
    ) -> None: ...
    def run(
        self,
        output_names: Sequence[str] | None,
        input_feed: Mapping[str, NDArray[np.float32] | NDArray[np.uint8]],
    ) -> list[NDArray[np.float32] | NDArray[np.uint8]]: ...
