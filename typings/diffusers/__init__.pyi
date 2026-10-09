from pathlib import Path
from typing import Self

import torch
import transformers
from PIL.Image import Image

class Flux2Transformer2DModel:
    def enable_layerwise_casting(
        self, storage_dtype: torch.dtype, compute_dtype: torch.dtype
    ) -> None: ...

class PipelineOutput:
    images: list[Image]

class Flux2KleinInpaintPipeline:
    transformer: Flux2Transformer2DModel
    @classmethod
    def from_pretrained(
        cls,
        path: Path,
        *,
        torch_dtype: torch.dtype,
        text_encoder: transformers.Qwen3ForCausalLM | None = ...,
        tokenizer: transformers.AutoTokenizer | None = ...,
        transformer: None = ...,
        vae: None = ...,
    ) -> Self: ...
    def encode_prompt(
        self, prompt: str, device: torch.device
    ) -> tuple[torch.Tensor, torch.Tensor]: ...
    def enable_model_cpu_offload(self) -> None: ...
    def set_progress_bar_config(self, *, disable: bool) -> None: ...
    def __call__(
        self,
        *,
        prompt_embeds: torch.Tensor,
        image: Image,
        mask_image: Image,
        height: int,
        width: int,
        strength: float,
        num_inference_steps: int,
        guidance_scale: float,
        generator: torch.Generator,
    ) -> PipelineOutput: ...
