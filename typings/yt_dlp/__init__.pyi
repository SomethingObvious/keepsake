from collections.abc import Mapping
from types import TracebackType
from typing import Self

from yt_dlp import utils as utils

class YoutubeDL:
    def __init__(self, params: Mapping[str, object]) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def prepare_filename(self, info_dict: Mapping[str, object]) -> str: ...
