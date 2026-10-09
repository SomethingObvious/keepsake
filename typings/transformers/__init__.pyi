from pathlib import Path
from typing import Self

import torch

class AutoTokenizer:
    @classmethod
    def from_pretrained(cls, path: Path) -> AutoTokenizer: ...

class Qwen3ForCausalLM:
    @classmethod
    def from_pretrained(cls, path: Path, *, torch_dtype: torch.dtype) -> Self: ...
    def to(self, device: str) -> Self: ...
