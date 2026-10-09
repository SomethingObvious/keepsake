r"""Taking the text laid over downloaded pictures off them: setting the remover up, and running it.

The remover (`detext/`) runs in a Python environment of its own under
%LOCALAPPDATA%\Keepsake\text-removal, because what it needs (ONNX Runtime,
and for the best tier PyTorch and two large downloads) has no place in
Keepsake's own. Two tiers:

* quick: runs on any computer, on the processor. PP-OCRv6 finds the lines, the
    overlay network (trained for this, fetched from this repository) and the
    small judge must both say a line was added, and LaMa paints what the
    overlay covered. About 2.3 GB.
* best: needs an NVIDIA card with 8 GB. The large judge gives the second
    opinion, and FLUX.2 [klein] 4B paints. About 28 GB.

Setting a tier up is a queue job, so it shows its progress and can be
cancelled; every file is pinned to a revision and checked against its hash.
"""

import functools
import hashlib
import json
import os
import shutil
import urllib.request
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Final

from keepsake import APP, media, paths, process, store, winapi
from keepsake.jobs import Job, Outcome, execute

TIERS: Final = ("quick", "best")
# What the remover can write back without touching what it did not change:
# JPEG block by block, PNG and WebP losslessly.
PICTURES: Final = frozenset({".jpg", ".jpeg", ".jfif", ".png", ".webp"})
# Raise when what a tier installs changes, so an older setup is done again.
SETUP_VERSION: Final = "1"
CHUNK: Final = 1 << 20
GB: Final = 1 << 30
LEAST_VRAM_GB: Final = 7.5  # an "8 GB" card reports a little under 8
UNBUFFERED: Final = "-u"  # so progress arrives as it happens

QUICK_PACKAGES: Final[tuple[str, ...]] = (
    "numpy==2.5.3",
    "opencv-python==5.0.0.93",
    "onnxruntime==1.30.0",
    "rapidocr==3.9.2",
    "jpeglib==1.0.2",
    "pillow==12.3.0",
)
TORCH: Final[tuple[str, ...]] = ("torch==2.11.0+cu128",)
TORCH_INDEX: Final = "https://download.pytorch.org/whl/cu128"
# What the packages take on disk, measured on this setup, for the settings to say.
QUICK_INSTALL: Final = 260 * (1 << 20)
BEST_INSTALL: Final = 4600 * (1 << 20)
BEST_PACKAGES: Final[tuple[str, ...]] = (
    "diffusers==0.40.0",
    "transformers==5.17.0",
    "accelerate==1.15.0",
    "safetensors==0.8.0",
)


@dataclass(frozen=True)
class Download:
    """A file fetched from a pinned place, into the models folder."""

    url: str
    to: str  # relative to the models folder
    size: int
    sha256: str = ""  # small configuration files are pinned by revision alone


def hugging(source: tuple[str, str], name: str, to: str, size: int, sha256: str = "") -> Download:
    """Return a file from a Hugging Face repository (name, revision) at that fixed revision."""
    repo, revision = source
    return Download(f"https://huggingface.co/{repo}/resolve/{revision}/{name}", to, size, sha256)


KLEIN: Final = ("black-forest-labs/FLUX.2-klein-4B", "e7b7dc27f91deacad38e78976d1f2b499d76a294")
JUDGE: Final = ("unsloth/Qwen3.5-9B-GGUF", "3885219b6810b007914f3a7950a8d1b469d598a5")
JUDGE_SMALL: Final = ("unsloth/Qwen3.5-2B-GGUF", "f6d5376be1edb4d416d56da11e5397a961aca8ae")
# The network is not in the installer: it comes from the repository at this tag, on setup.
NETWORK_TAG: Final = "overlay-network-1"
SERVER: Final = "https://github.com/ggml-org/llama.cpp/releases/download/b9553/"
SERVER_ZIP: Final = "llama/llama-b9553-bin-win-vulkan-x64.zip"
SERVER_CPU_ZIP: Final = "llama-cpu/llama-b9553-bin-win-cpu-x64.zip"

QUICK_FILES: Final = (
    Download(
        f"https://raw.githubusercontent.com/SomethingObvious/keepsake/{NETWORK_TAG}/detext/overlay.onnx",
        "overlay.onnx",
        18369363,
        "d200e7dcc32e65da2ac97aef9a7f56b832fc1b037a06311971390cabcefb0900",
    ),
    hugging(
        ("Carve/LaMa-ONNX", "c3c0c9e468934d62e79c329e35d82dd09ff8c444"),
        "lama_fp32.onnx",
        "lama.onnx",
        208044816,
        "1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6",
    ),
    hugging(
        JUDGE_SMALL,
        "Qwen3.5-2B-Q4_K_M.gguf",
        "judge-small/model.gguf",
        1280835840,
        "aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223",
    ),
    hugging(
        JUDGE_SMALL,
        "mmproj-F16.gguf",
        "judge-small/projector.gguf",
        668227264,
        "7035e9cb8d7c6a9681d07eef9a364783e86ea4cd73faab2eabb4f43a101830c7",
    ),
    Download(
        SERVER + "llama-b9553-bin-win-cpu-x64.zip",
        SERVER_CPU_ZIP,
        16935222,
        "cfa021204e28f76ada68a259e3f888db1261ee19a03f9fee171b8fe75a3d5226",
    ),
)
BEST_FILES: Final = (
    *(
        hugging(KLEIN, name, f"klein/{name}", size, sha)
        for name, size, sha in (
            ("model_index.json", 446, ""),
            ("scheduler/scheduler_config.json", 486, ""),
            ("text_encoder/config.json", 1536, ""),
            ("text_encoder/generation_config.json", 214, ""),
            (
                "text_encoder/model-00001-of-00002.safetensors",
                4967215360,
                "8c0506e7f4936fa7e26183a4fd8da4e2bdbc5990ba64ae441f965d51228f36ea",
            ),
            (
                "text_encoder/model-00002-of-00002.safetensors",
                3077766632,
                "82f2bd839378541b0557bfabaf37c7d3d637071fdcb73302dedd7cf61162ce07",
            ),
            ("text_encoder/model.safetensors.index.json", 32855, ""),
            ("tokenizer/added_tokens.json", 707, ""),
            ("tokenizer/chat_template.jinja", 4168, ""),
            ("tokenizer/merges.txt", 1671853, ""),
            ("tokenizer/special_tokens_map.json", 613, ""),
            (
                "tokenizer/tokenizer.json",
                11422654,
                "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
            ),
            ("tokenizer/tokenizer_config.json", 5404, ""),
            ("tokenizer/vocab.json", 2776833, ""),
            ("transformer/config.json", 541, ""),
            (
                "transformer/diffusion_pytorch_model.safetensors",
                7751109744,
                "9f29f9edcfdae452a653ffb51a534ca4decd389952c225724ff3b94042612a6e",
            ),
            ("vae/config.json", 821, ""),
            (
                "vae/diffusion_pytorch_model.safetensors",
                168120878,
                "ca70d2202afe6415bdbcb8793ba8cd99fd159cfe6192381504d6c4d3036e0f04",
            ),
        )
    ),
    hugging(
        JUDGE,
        "Qwen3.5-9B-Q4_K_M.gguf",
        "judge/model.gguf",
        5680522464,
        "03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8",
    ),
    hugging(
        JUDGE,
        "mmproj-F16.gguf",
        "judge/projector.gguf",
        918166080,
        "f70dc3509053962b0d0d3ee8a7eacebf5d60aa560cad78254ae8698516ae029f",
    ),
    Download(
        SERVER + "llama-b9553-bin-win-vulkan-x64.zip",
        SERVER_ZIP,
        33930642,
        "71ce19ec77d6eddcaff520f6ba2c0e90c28755d0ec2851c2375042ecddbb9bba",
    ),
)


def home() -> Path:
    """Return the remover's folder; read at call time, so a test can move it."""
    return paths.TEXT_REMOVAL


def models() -> Path:
    """Return where the models are kept."""
    return home() / "models"


def python() -> Path:
    """Return the remover's own Python."""
    return home() / "env" / "Scripts" / "python.exe"


def marker(tier: str) -> Path:
    """Return the file that says a tier is set up."""
    return home() / f"{tier}.ready"


def ready(tier: str) -> bool:
    """Return whether a tier is set up, and by this version of Keepsake's setup."""
    try:
        return marker(tier).read_text(encoding="utf-8").strip() == SETUP_VERSION
    except OSError:
        return False


@functools.cache  # the card does not change while Keepsake runs, and asking starts a program
def graphics_card() -> tuple[str, float] | None:
    """Return the NVIDIA card's name and memory in GB, or None when there is none."""
    line = process.first_line(
        [paths.tool("nvidia-smi"), "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
    )
    if not line or "," not in line:
        return None
    name, memory = line.rsplit(",", 1)
    try:
        return name.strip(), float(memory) / 1024
    except ValueError:
        return None


def status() -> dict[str, object]:
    """Return what the settings show: which tiers are ready, and whether best can run here."""
    card = graphics_card()
    return {
        "quick": ready("quick"),
        "best": ready("best"),
        "card": card[0] if card else "",
        "best_possible": bool(card and card[1] >= LEAST_VRAM_GB),
        "quick_size": QUICK_INSTALL + sum(f.size for f in QUICK_FILES),
        "best_size": BEST_INSTALL + sum(f.size for f in (*QUICK_FILES, *BEST_FILES)),
    }


def files_for(tier: str) -> tuple[Download, ...]:
    """Return every file a tier downloads."""
    return (*QUICK_FILES, *BEST_FILES) if tier == "best" else QUICK_FILES


def packages_for(tier: str) -> list[list[str]]:
    """Return the pip commands, argument lists after `pip install`, that a tier needs."""
    commands: list[list[str]] = [list(QUICK_PACKAGES)]
    if tier == "best":
        commands.append([*TORCH, "--index-url", TORCH_INDEX])
        commands.append(list(BEST_PACKAGES))
    return commands


def sha256(path: Path, job: Job) -> str:
    """Return a file's SHA-256, stopping early if the job is."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK * 8):
            if job.stopped():
                return ""
            digest.update(chunk)
    return digest.hexdigest()


def good(path: Path, want: Download, job: Job) -> bool:
    """Return whether a downloaded file is the one pinned: its size, and its hash where known."""
    if not path.is_file() or path.stat().st_size != want.size:
        return False
    return not want.sha256 or sha256(path, job) == want.sha256


def fetch(want: Download, job: Job, done: int, total: int) -> int:
    """Download one file, resuming a partial one, and return the bytes now done overall."""
    target = models() / want.to
    if good(target, want, job):
        return done + want.size
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    have = partial.stat().st_size if partial.is_file() else 0
    if have > want.size:
        partial.unlink()
        have = 0
    request = urllib.request.Request(want.url, headers={"User-Agent": APP})
    if have:
        request.add_header("Range", f"bytes={have}-")
    with urllib.request.urlopen(request, timeout=60) as reply, partial.open("ab") as sink:
        if have and reply.status != HTTPStatus.PARTIAL_CONTENT:  # it sent the whole file again
            sink.truncate(0)
            have = 0
        while chunk := reply.read(CHUNK):
            if job.stopped():
                return done + have
            sink.write(chunk)
            have += len(chunk)
            job.pct = 100.0 * (done + have) / total
    partial.replace(target)
    if not good(target, want, job):
        target.unlink(missing_ok=True)
        message = f"{want.to} did not match its pinned hash"
        raise ValueError(message)
    job.log.append(f"--- {want.to}: {want.size / GB:.2f} GB, checked")
    return done + want.size


def unpack(archive: Path) -> None:
    """Unzip the judge's server beside its zip."""
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(archive.parent)


def pip(job: Job, arguments: Sequence[str]) -> bool:
    """Run pip in the remover's environment, logging what it says."""
    job.stage = "Installing what it needs"
    command = [
        str(python()),
        UNBUFFERED,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        *arguments,
    ]
    return execute(job, command, job.log.append) == 0


def install(job: Job, tier: str) -> str:
    """Make the remover's Python and install a tier's packages; return any problem."""
    if not python().is_file():
        job.stage = "Making its own Python"
        if execute(job, [paths.PYTHON, "-m", "venv", str(home() / "env")], job.log.append) != 0:
            return "ERROR: could not make a Python environment for it"
    for arguments in packages_for(tier):
        if job.stopped():
            return ""
        if not pip(job, arguments):
            return "ERROR: installing its packages failed (see the log)"
    return ""


def download_all(job: Job, tier: str) -> None:
    """Fetch every model a tier needs, each checked against its pin."""
    wanted = files_for(tier)
    total, done = sum(f.size for f in wanted), 0
    job.stage = "Downloading its models"
    for want in wanted:
        done = fetch(want, job, done, total)
        if job.stopped():
            return
    for want in wanted:
        if want.to.endswith(".zip"):
            unpack(models() / want.to)


def set_up(job: Job) -> Outcome:
    """Set a tier up: its own Python, its packages, its models; then say it is ready."""
    tier = job.mode
    if tier not in TIERS:
        return False, f"ERROR: there is no {tier} text removal"
    if tier == "best" and not status()["best_possible"]:
        return False, "ERROR: the best text removal needs an NVIDIA graphics card with 8 GB"
    home().mkdir(parents=True, exist_ok=True)
    problem = install(job, tier)
    if not problem and not job.stopped():
        download_all(job, tier)
    if problem or job.stopped():
        return False, problem
    job.stage, job.pct = "Fetching the text detector, and trying it", None
    command = [str(python()), UNBUFFERED, "-m", "detext", "prepare", tier, str(models())]
    if execute(job, command, job.log.append, cwd=paths.ROOT) != 0:
        return False, "ERROR: the text remover did not start (see the log)"
    marker(tier).write_text(SETUP_VERSION, encoding="utf-8")
    return True, ""


def swap_in(original: Path, cleaned: Path) -> bool:
    """Put the cleaned picture in the original's place, and the original in the Recycle Bin.

    For pictures as they download. The Recycle Bin, so that a wrong removal is
    undone as any delete is. The cleaned file keeps the original's dates, so it
    sorts where it did.
    """
    when = original.stat()
    if not winapi.recycle(original):
        return False
    cleaned.replace(original)
    os.utime(original, ns=(when.st_atime_ns, when.st_mtime_ns))
    return True


def keep_beside(original: Path, cleaned: Path) -> Path:
    """Give the cleaned picture a name of its own beside the original, which stays as it was.

    For pictures already in the library: pressing the button makes a copy, the
    way Save Frame and Save Clip do, so nothing anyone kept is changed.
    """
    target = media.beside(original, "no text", original.suffix)
    cleaned.replace(target)
    return target


class Progress:
    """Reads the remover's lines into a job: its stage, its progress, and what each picture lost."""

    def __init__(self, job: Job) -> None:
        """Read into this job."""
        self.job = job
        self.cleaned = 0
        self.failed = 0

    def __call__(self, line: str) -> None:
        """Take one line of the remover's output."""
        try:
            said = store.record(json.loads(line))
        except ValueError:
            self.job.log.append(line)
            return
        done, total = said.get("done"), said.get("total")
        if isinstance(done, int) and isinstance(total, int) and total:
            self.job.pct = 100.0 * done / total
        stage = said.get("stage")
        if isinstance(stage, str):
            self.job.stage = stage
        if "file" in said:
            self.picture(said)

    def picture(self, said: dict[str, object]) -> None:
        """Put a cleaned picture where it goes, and log what happened to it."""
        name = Path(str(said.get("file", "")))
        state = str(said.get("status", ""))
        words = ", ".join(f'"{text}"' for text in store.items(said.get("removed")))
        output = Path(str(said.get("output", "")))
        if state == "cleaned" and self.job.job_kind == "convert":
            copy = keep_beside(name, output)
            self.job.add_file(str(copy))
            self.cleaned += 1
            self.job.log.append(f"--- {copy.name}: took off {words}")
        elif state == "cleaned" and swap_in(name, output):
            self.cleaned += 1
            self.job.log.append(f"--- {name.name}: took off {words}")
        elif state == "cleaned":
            self.failed += 1
            self.job.log.append(f"--- {name.name}: the original could not go to the Recycle Bin")
        elif state == "failed":
            self.failed += 1
            self.job.log.append(f"--- {name.name}: {said.get('error', 'failed')}")
        else:
            self.job.log.append(f"--- {name.name}: no added text")
        for key, meaning in (
            ("unsure", "left, as the checks disagreed"),
            ("still_there", "may still show"),
            ("restored", "put back, as it crossed text in the picture"),
        ):
            for text in store.items(said.get(key)):
                self.job.log.append(f'    "{text}" {meaning}')


def chosen(job: Job) -> str:
    """Return the tier to use: the options' choice, or for the library's button, the best set up."""
    tier = job.options.remove_text
    if tier in TIERS or job.job_kind != "convert":
        return tier
    return next((t for t in reversed(TIERS) if ready(t)), "quick")


def remove_text(job: Job, pictures: Sequence[Path], tier: str) -> Outcome:
    """Take the added text off these pictures with one tier."""
    if tier not in TIERS or not pictures:
        return True, ""
    if not ready(tier):
        job.log.append(f"--- text removal ({tier}) is not set up yet: Options, Galleries")
        return True, ""
    tool, job.tool = job.tool, "text removal"
    reader = Progress(job)
    command = [str(python()), UNBUFFERED, "-m", "detext", tier, str(models()), *map(str, pictures)]
    code = execute(job, command, reader, cwd=paths.ROOT)
    job.tool = tool
    if job.stopped():
        return False, ""
    if code != 0:
        return False, f"ERROR: the text remover stopped with exit code {code}"
    if len(pictures) > 1:
        job.stage = f"Took the added text off {reader.cleaned} of {len(pictures)}"
    else:
        job.stage = (
            "Took the added text off" if reader.cleaned else "Found no added text it was sure of"
        )
    return True, ""


def forget() -> None:
    """Remove the remover and its models entirely."""
    shutil.rmtree(home(), ignore_errors=True)
