"""The best tier's painter: FLUX.2 [klein] 4B, inpainting, on the NVIDIA card.

It regenerates only the hole, with the untouched photo around it and the
original as its reference, so a sign half-hidden by a caption comes back as
the rest of that sign rather than as a new one. PyTorch is imported only when
the painter is made: the quick tier's environment does not have it.
"""

import gc
from pathlib import Path
from typing import Final

import cv2
import numpy as np
from PIL import Image as PILImage

from detext.layers import Mask
from detext.pipeline import Picture

# Klein: the distilled 4B runs in 4 steps at guidance 1. Each hole is painted
# in a crop around it with this much context, capped at about a megapixel.
PROMPT: Final = (
    "Remove the text, stickers and watermarks added on top of this photo, and anything drawn"
    " behind them. Keep everything else exactly as it is."
)
STEPS: Final = 4
CONTEXT: Final = 0.6
LEAST_CROP: Final = 512
MOST_PIXELS: Final = 1024 * 1024
LATENT: Final = 16
GATHER: Final = 65


class Klein:
    """FLUX.2 [klein] 4B inpainting, stored in fp8 so that it fits on an 8 GB card."""

    def __init__(self, folder: Path) -> None:
        """Encode the one prompt, free the text encoder, then load the painter."""
        import torch
        import transformers
        from diffusers import Flux2KleinInpaintPipeline
        from diffusers.hooks import apply_layerwise_casting

        tokenizer = transformers.AutoTokenizer.from_pretrained(folder / "tokenizer")
        encoder = transformers.Qwen3ForCausalLM.from_pretrained(
            folder / "text_encoder", torch_dtype=torch.bfloat16
        )
        apply_layerwise_casting(
            encoder,
            storage_dtype=torch.float8_e4m3fn,
            compute_dtype=torch.bfloat16,
            skip_modules_pattern=("embed", "norm", "lm_head"),
        )
        encoder.to("cuda")
        pipe = Flux2KleinInpaintPipeline.from_pretrained(
            folder,
            text_encoder=encoder,
            tokenizer=tokenizer,
            transformer=None,
            vae=None,
            torch_dtype=torch.bfloat16,
        )
        with torch.inference_mode():
            self.prompt, _ = pipe.encode_prompt(prompt=PROMPT, device=torch.device("cuda"))
        del pipe, encoder
        gc.collect()
        torch.cuda.empty_cache()
        self.pipe = Flux2KleinInpaintPipeline.from_pretrained(
            folder, text_encoder=None, tokenizer=None, torch_dtype=torch.bfloat16
        )
        self.pipe.transformer.enable_layerwise_casting(
            storage_dtype=torch.float8_e4m3fn, compute_dtype=torch.bfloat16
        )
        self.pipe.enable_model_cpu_offload()
        self.pipe.set_progress_bar_config(disable=True)

    def paint(self, crop: Picture, hole: Mask) -> Picture:
        """Inpaint one crop, whose sides are multiples of 16."""
        import torch

        height, width = hole.shape
        with torch.inference_mode():
            result = self.pipe(
                prompt_embeds=self.prompt,
                image=PILImage.fromarray(crop),
                mask_image=PILImage.fromarray(hole.astype(np.uint8) * 255),
                height=height,
                width=width,
                strength=1.0,
                num_inference_steps=STEPS,
                guidance_scale=1.0,
                generator=torch.Generator("cpu").manual_seed(0),
            ).images[0]
        return np.asarray(result.convert("RGB"))[:height, :width]

    def __call__(self, picture: Picture, hole: Mask) -> Picture:
        """Return the picture with `hole` painted in, one crop per group of nearby holes."""
        out = picture.copy()
        height, width = hole.shape
        groups = cv2.dilate(hole.astype(np.uint8), np.ones((GATHER, GATHER), np.uint8))
        count, _, stats, _ = cv2.connectedComponentsWithStats(groups)
        for index in range(1, count):
            left, top, wide, tall = (int(v) for v in stats[index, :4])
            x0, y0, x1, y1 = crop_box((left, top, wide, tall), (width, height))
            crop, part = out[y0:y1, x0:x1], hole[y0:y1, x0:x1]
            scale = min(1.0, (MOST_PIXELS / (crop.shape[0] * crop.shape[1])) ** 0.5)
            size = (snap(crop.shape[1] * scale), snap(crop.shape[0] * scale))
            small = np.asarray(cv2.resize(crop, size, interpolation=cv2.INTER_AREA), dtype=np.uint8)
            small_hole = (
                cv2.resize(part.astype(np.uint8), size, interpolation=cv2.INTER_NEAREST) > 0
            )
            painted = self.paint(
                small, cv2.dilate(small_hole.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            )
            back = cv2.resize(
                painted, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_CUBIC
            )
            crop[part] = back[part]
        return out


def snap(value: float) -> int:
    """Round a side to a multiple of 16, the size of one latent patch, at least one patch."""
    return max(LATENT, round(value / LATENT) * LATENT)


def span(start: int, size: int, extra: int, limit: int) -> tuple[int, int]:
    """Return one side of a crop: the holes and context, at least 512 px, inside the picture."""
    low, high = start - extra, start + size + extra
    short = LEAST_CROP - (high - low)
    if short > 0:
        low, high = low - short // 2, high + short - short // 2
    if low < 0:
        low, high = 0, high - low
    if high > limit:
        low, high = low - (high - limit), limit
    return max(0, low), min(limit, high)


def crop_box(
    holes: tuple[int, int, int, int], picture: tuple[int, int]
) -> tuple[int, int, int, int]:
    """Return a crop (left, top, right, bottom) around holes (left, top, width, height)."""
    left, top, wide, tall = holes
    width, height = picture
    extra = round(CONTEXT * max(wide, tall))
    x0, x1 = span(left, wide, extra, width)
    y0, y1 = span(top, tall, extra, height)
    return x0, y0, x1, y1
