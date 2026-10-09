"""The second opinion: a judge that looks at the picture, run in its own local server.

It is asked once per picture about every line the detector found, and a line
is removed only when it and the overlay network both say it was added. The
best tier runs the large judge on the NVIDIA card, and the quick tier runs the
small one on the processor at a smaller picture size, which is slower to answer
but just as unwilling to call a sign "added" (see DETEXT.md). Either way the
worker asks about every picture first and closes the judge before painting.
"""

import base64
import contextlib
import http.client
import io
import json
import re
import socket
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import Final, Self, cast

import numpy as np
from PIL import Image as PILImage

from detext.pipeline import Line, Picture

# What the judge is told. Measured on 270 lines (DETEXT.md): the clause about
# graphic designs is what stopped a book cover's title being called added.
QUESTION: Final = (
    "This picture was downloaded from social media. Some of the text in it may have been added"
    " on top of the picture afterwards, in an app or editor: captions, story text, stickers,"
    " @usernames, hashtags, watermarks, app logos, subtitles.\n"
    "Other text is part of the picture itself: signs, shop fronts, neon, clothing, packaging,"
    " screens, posters, book covers, labels, anything printed or painted on something in the"
    " scene.\n"
    "Some pictures are themselves a graphic design: a book or album cover, a poster, a flyer, an"
    " advert, a title card. The lettering designed into it is part of the picture too, even"
    " though it was made on a computer. Only text laid over the finished picture afterwards (a"
    " caption, a username, a sticker) counts as added.\n"
    "\n"
    "Here is every piece of text found in the picture, with where it is:\n"
    "{lines}\n"
    "\n"
    'For each number, answer "added" only if that text was clearly put on top of the picture'
    ' afterwards. Answer "scene" if it is part of the picture itself. If you are not sure,'
    ' answer "scene".\n'
    'Reply with JSON only, like {{"1": "scene", "2": "added"}}.'
)
# Asked first, on the card: a designed graphic's own lettering is not an overlay.
DESIGN: Final = (
    "Is this picture itself a piece of graphic design, such as a book or album cover, a poster,"
    " a flyer, an advert or a title card, made on a computer as one whole? Or is it a photograph"
    " (or a still from a video) that someone may have put text or stickers on afterwards? A"
    " photograph of a poster or a sign is a photograph."
    ' Reply with JSON only: {"design": true} or {"design": false}.'
)
DESIGN_TOKENS: Final = 50
# The picture's longest side as the judge sees it: on a card, and on a processor.
CARD_SIDE: Final = 1024
PROCESSOR_SIDE: Final = 768
THIRD: Final = 1 / 3
START_SECONDS: Final = 300
ANSWER_SECONDS: Final = 600
TOKENS: Final = 1200


def where(quad: np.ndarray, width: int, height: int) -> str:
    """Describe where a line is, in words and in percent of the picture."""
    xs, ys = quad[:, 0], quad[:, 1]
    across = (xs.min() + xs.max()) / 2 / width
    down = (ys.min() + ys.max()) / 2 / height
    column = "left" if across < THIRD else "right" if across > 2 * THIRD else "middle"
    row = "top" if down < THIRD else "bottom" if down > 2 * THIRD else "centre"
    return (
        f"{row} {column}, x {xs.min() / width:.0%}-{xs.max() / width:.0%},"
        f" y {ys.min() / height:.0%}-{ys.max() / height:.0%}"
    )


def free_port() -> int:
    """Return a port nothing is listening on."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class Judge:
    """The judge's server, running for as long as the `with` lasts."""

    def __init__(self, server: Path, model: Path, projector: Path, *, on_card: bool) -> None:
        """Remember what to start, and where: the NVIDIA card, or the processor."""
        self.server, self.model, self.projector = server, model, projector
        self.on_card = on_card
        self.side = CARD_SIDE if on_card else PROCESSOR_SIDE
        self.process: subprocess.Popen[bytes] | None = None
        self.port = 0

    def device(self) -> list[str]:
        """Return where the server runs: the NVIDIA card (not an integrated one), or the CPU."""
        if not self.on_card:
            return ["--device", "none", "-ngl", "0", "--no-mmproj-offload"]
        listing = subprocess.run(
            [str(self.server), "--list-devices"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in (listing.stdout + listing.stderr).splitlines():
            found = re.match(r"\s*(\w+\d+):\s.*NVIDIA", line)
            if found:
                return ["--device", found.group(1), "-ngl", "99"]
        return ["-ngl", "99"]

    def __enter__(self) -> Self:
        """Start the server and wait until it answers."""
        self.port = free_port()
        self.process = subprocess.Popen(
            [
                str(self.server),
                *("-m", str(self.model), "--mmproj", str(self.projector)),
                *self.device(),
                *("-c", "4096", "--host", "127.0.0.1", "--port", str(self.port)),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        deadline = time.monotonic() + START_SECONDS
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                message = "the judge's server stopped as it started"
                raise RuntimeError(message)
            with contextlib.suppress(OSError, http.client.HTTPException):
                if b"ok" in self.ask("GET", "/health", None, timeout=5):
                    return self
            time.sleep(1)
        message = "the judge's server did not start"
        raise RuntimeError(message)

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Stop the server, freeing the graphics card for the painter."""
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=30)

    def __call__(self, picture: Picture, lines: Sequence[Line]) -> list[bool]:
        """Return, for each line, whether the judge says it was added on top.

        On the card, it is first asked whether the whole picture is a piece of
        graphic design: a book cover's own title reads as "added" to the
        network and to the judge alike, so a design is left as it is. That
        also leaves some heavily captioned memes alone, which is the side to
        err on.
        """
        height, width = picture.shape[:2]
        image = PILImage.fromarray(picture)
        image.thumbnail((self.side, self.side), PILImage.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=93)
        seen = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()
        if self.on_card and designed(self.chat(seen, DESIGN, DESIGN_TOKENS)):
            return [False] * len(lines)
        listing = "\n".join(
            f'{number}. "{line.text}" ({where(line.quad, width, height)})'
            for number, line in enumerate(lines, 1)
        )
        return verdicts(self.chat(seen, QUESTION.format(lines=listing), TOKENS), len(lines))

    def chat(self, picture: str, question: str, tokens: int) -> str:
        """Ask one question about a picture (a data URL) and return the answer."""
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": picture}},
                        {"type": "text", "text": question},
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        reply = self.ask("POST", "/v1/chat/completions", json.dumps(body).encode(), ANSWER_SECONDS)
        return str(json.loads(reply)["choices"][0]["message"]["content"])

    def ask(self, method: str, path: str, body: bytes | None, timeout: float) -> bytes:
        """Send one request to the server on this machine and return the body of its reply."""
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            connection.request(method, path, body, {"Content-Type": "application/json"})
            return connection.getresponse().read()
        finally:
            connection.close()


def reply(answer: str) -> dict[str, object]:
    """Read the JSON object a judge's answer holds; anything unreadable is empty."""
    start = answer.find("{")
    try:
        parsed: object = json.JSONDecoder().raw_decode(answer[start:])[0] if start >= 0 else {}
    except ValueError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): value for key, value in cast("dict[object, object]", parsed).items()}


def designed(answer: str) -> bool:
    """Read the design question's reply; only a clear "no" lets the lines be judged."""
    return reply(answer).get("design") is not False


def verdicts(answer: str, count: int) -> list[bool]:
    """Read the judge's JSON reply; anything missing or unreadable is "scene"."""
    said = reply(answer)
    return [
        str(said.get(str(number), "scene")).lower().startswith("add")
        for number in range(1, count + 1)
    ]
