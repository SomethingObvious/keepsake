"""Fetch the static ARM64 FFmpeg the app carries, check it, and name it as Android needs.

It is wader/static-ffmpeg, built against musl: Android's app sandbox kills a
glibc build on its first unusual system call, and musl makes none. It is only
published as a container image, so this takes the one layer straight from the
registry, by its digest. Android only runs programs from an app's own library
folder, and only files named lib*.so get copied there, so ffmpeg becomes
libffmpeg.so.

    python scripts/fetch_ffmpeg.py OUT_DIR
"""

import hashlib
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

IMAGE = "mwader/static-ffmpeg"
VERSION = "9.0.2-1-arm64"
LAYER = "sha256:b97d6d5fc8d13dca24a7b71a33f28a32836db81b22673edb4beb6020b10a0272"
REGISTRY = "https://registry-1.docker.io/v2"


def fetch(url: str, token: str = "") -> bytes:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=600) as reply:
        return reply.read()


def main() -> None:
    out = Path(sys.argv[1])
    cache = out.parent.parent / f"static-ffmpeg-{VERSION}.tar.gz"
    if not cache.is_file():
        auth = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{IMAGE}:pull"
        token = json.loads(fetch(auth))["token"]
        cache.write_bytes(fetch(f"{REGISTRY}/{IMAGE}/blobs/{LAYER}", token))
    digest = "sha256:" + hashlib.sha256(cache.read_bytes()).hexdigest()
    if digest != LAYER:
        cache.unlink()
        raise SystemExit(f"{IMAGE}:{VERSION} came back as {digest}, not {LAYER}")
    out.mkdir(parents=True, exist_ok=True)
    with tarfile.open(cache) as layer:
        for name in ("ffmpeg", "ffprobe"):
            data = layer.extractfile(name)
            if data is None:
                raise SystemExit(f"{IMAGE}:{VERSION} has no {name}")
            (out / f"lib{name}.so").write_bytes(data.read())


if __name__ == "__main__":
    main()
