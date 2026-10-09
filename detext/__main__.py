"""Take the added text off pictures: `python -m detext quick|best <models folder> <picture>...`.

`python -m detext prepare quick|best <models folder>` fetches the text
detector and loads everything once, so setup fails where running would.

Prints one JSON object per line: what it is doing, then one per picture:
{"file", "status": cleaned | clean | skipped | failed, "output", "removed",
"kept", "unsure", "still_there", "restored", "error"}. A cleaned picture is
written beside the original as "<name>.cleaned<ext>", and Keepsake decides
where it goes.
"""

import json
import sys
import tempfile
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

import numpy as np
from PIL import Image as PILImage

from detext import layers
from detext.judge import Judge as Server
from detext.lama import Lama
from detext.pipeline import (
    COVERED,
    Fill,
    Judge,
    Line,
    Outcome,
    Overlay,
    Picture,
    Reader,
    clean,
    coverage,
    load,
)

HERE = Path(__file__).resolve().parent
# Pictures it can write back without losing anything it did not change.
WRITABLE: Final = frozenset({".jpg", ".jpeg", ".jfif", ".png", ".webp"})
PASSES: Final = 2


def network(models: Path) -> Path:
    """Return the overlay network: set up with the models, or beside this file in a checkout."""
    downloaded = models / "overlay.onnx"
    return downloaded if downloaded.is_file() else HERE / "overlay.onnx"


def say(**fields: object) -> None:
    """Print one line of the protocol."""
    sys.stdout.write(json.dumps(fields, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def cleaned_name(path: Path) -> Path:
    """Return where a picture's cleaned copy is written."""
    return path.with_name(f"{path.stem}.cleaned{path.suffix}")


def write(path: Path, picture: Picture, changed: layers.Mask) -> Path:
    """Write the cleaned picture beside the original, changing nothing the cleaning did not."""
    target = cleaned_name(path)
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".jfif"}:
        with tempfile.TemporaryDirectory() as scratch:
            layers.splice_jpeg(
                str(path), picture, changed, str(target), str(Path(scratch) / "blocks.jpg")
            )
        return target
    with PILImage.open(path) as original:
        alpha = original.getchannel("A") if "A" in original.getbands() else None
        image = PILImage.fromarray(picture)
        if alpha is not None:
            image.putalpha(alpha)
        if suffix == ".webp":
            image.save(target, "WEBP", lossless=True, exact=True)
        else:
            image.save(target, "PNG", optimize=True)
    return target


def restore_scene(original: Picture, outcome: Outcome, scene: Sequence[Line]) -> list[str]:
    """Put back the pixels of any scene line that no longer reads the same; return which."""
    if outcome.result is None or outcome.changed is None or not outcome.scene_changed:
        return []
    shape = original.shape[:2]
    restored: list[str] = []
    for line in scene:
        if line.text in outcome.scene_changed:
            box = layers.grow(line.mask(shape), 2) & outcome.changed
            outcome.result[box] = original[box]
            outcome.changed &= ~box
            restored.append(line.text)
    return restored


def one(
    path: Path, reader: Reader, overlay: Overlay, fill: Fill, judge: Judge | None
) -> dict[str, object]:
    """Clean one picture and return its line of the protocol."""
    if path.suffix.lower() not in WRITABLE:
        return {"status": "skipped", "error": f"{path.suffix} pictures are not supported"}
    original = load(path)
    picture = original
    total = Outcome()
    changed = np.zeros(picture.shape[:2], dtype=bool)
    for _ in range(PASSES):
        outcome = clean(picture, reader, overlay, fill, judge)
        if outcome.result is None or outcome.changed is None:
            if not total.removed:
                total = outcome
            break
        scene = [line for line in reader.lines(picture) if line.text in outcome.kept]
        restored = restore_scene(original, outcome, scene)
        total.removed += outcome.removed
        total.kept, total.unsure = outcome.kept, outcome.unsure
        total.still_there, total.scene_changed = outcome.still_there, restored
        changed |= outcome.changed
        picture = outcome.result
        if not outcome.still_there:
            break
        judge = None  # the second pass only reruns what the network still sees
    if not total.removed:
        return {"status": "clean", "kept": total.kept, "unsure": total.unsure}
    output = write(path, picture, changed)
    return {
        "status": "cleaned",
        "output": str(output),
        "removed": total.removed,
        "kept": total.kept,
        "unsure": total.unsure,
        "still_there": total.still_there,
        "restored": total.scene_changed,
    }


def judge_for(tier: str, models: Path) -> Server:
    """Return the tier's judge: the large one on the card, or the small one on the processor."""
    if tier == "best":
        return Server(
            models / "llama" / "llama-server.exe",
            models / "judge" / "model.gguf",
            models / "judge" / "projector.gguf",
            on_card=True,
        )
    return Server(
        models / "llama-cpu" / "llama-server.exe",
        models / "judge-small" / "model.gguf",
        models / "judge-small" / "projector.gguf",
        on_card=False,
    )


def judged(
    files: Sequence[Path], reader: Reader, overlay: Overlay, judge: Server
) -> Callable[[Path], Judge]:
    """Ask the judge about every picture first, then close it; return the answers."""
    answers: dict[Path, list[bool]] = {}
    with judge as ask:
        for number, path in enumerate(files, 1):
            say(stage="Checking each line", done=number - 1, total=len(files))
            if path.suffix.lower() not in WRITABLE:
                continue
            picture = load(path)
            lines = reader.lines(picture)
            hard, _ = overlay.alphas(picture)
            if any(coverage(line, hard) >= COVERED for line in lines):
                answers[path] = ask(picture, lines)

    def for_file(path: Path) -> Judge:
        def answer(_picture: Picture, lines: Sequence[Line]) -> list[bool]:
            return answers.get(path, [False] * len(lines))

        return answer

    return for_file


def prepare(tier: str, models: Path) -> int:
    """Fetch the text detector's models and load the tier's parts once."""
    reader = Reader(models / "ocr")
    Overlay(network(models))
    if tier == "best":
        import torch  # only the best tier installs it

        if not torch.cuda.is_available():
            say(error="PyTorch cannot see an NVIDIA graphics card")
            return 1
    else:
        Lama(models / "lama.onnx")
    blank = np.full((64, 256, 3), 255, dtype=np.uint8)
    reader.lines(blank)
    with judge_for(tier, models) as ask:
        ask(blank, [])
    say(stage="Ready")
    return 0


def main(argv: Sequence[str]) -> int:
    """Clean each picture named, reporting as it goes."""
    if argv[0] == "prepare":
        return prepare(argv[1], Path(argv[2]))
    tier, models, files = argv[0], Path(argv[1]), [Path(a) for a in argv[2:]]
    say(stage="Loading the text remover", done=0, total=len(files))
    reader = Reader(models / "ocr")
    overlay = Overlay(network(models))
    judges = judged(files, reader, overlay, judge_for(tier, models))
    say(stage="Loading the painter", done=0, total=len(files))
    if tier == "best":
        from detext.klein import Klein  # needs PyTorch, which only the best tier installs

        fill: Fill = Klein(models / "klein")
    else:
        fill = Lama(models / "lama.onnx")
    for number, path in enumerate(files, 1):
        say(stage="Removing added text", done=number - 1, total=len(files))
        try:
            report = one(path, reader, overlay, fill, judges(path))
        except Exception as problem:  # one bad picture must not stop the rest
            report = {
                "status": "failed",
                "error": f"{type(problem).__name__}: {problem}",
                "trace": traceback.format_exc(limit=3),
            }
        say(file=str(path), **report)
    say(stage="Done", done=len(files), total=len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
