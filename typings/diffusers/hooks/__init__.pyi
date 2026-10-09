from collections.abc import Sequence

import torch

def apply_layerwise_casting(
    module: object,
    storage_dtype: torch.dtype,
    compute_dtype: torch.dtype,
    skip_modules_pattern: Sequence[str] = ...,
) -> None: ...
