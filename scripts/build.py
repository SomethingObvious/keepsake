r"""Build the Windows installer, and the app zip that installed copies update from.

    python scripts/build.py

The installer carries Keepsake, its own Python and the packages it needs.
FFmpeg and Deno are fetched by the app on its first start instead, from where
their makers publish them. Downloads are kept in build\cache, and the results
go in dist\: KeepsakeSetup.exe and keepsake-app-<version>.zip. The installer
keeps one name, so releases/latest/download/KeepsakeSetup.exe is always the
newest. Needs Inno Setup 6.
"""

import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD, DIST = ROOT / "build", ROOT / "dist"
STAGE = BUILD / "Keepsake"
PYTHON = "3.12.10"
PYTHON_URL = f"https://www.nuget.org/api/v2/package/python/{PYTHON}"
APP_PARTS = ("keepsake", "ui", "assets", "launch.pyw", "requirements.txt", "LICENSE")
# Headers and import libraries are only for compiling, which nothing here does.
UNUSED = ("include", "libs")
ISCC = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"


def version() -> str:
    """Return the version keepsake/__init__.py declares."""
    source = (ROOT / "keepsake" / "__init__.py").read_text(encoding="utf-8")
    found = re.search(r'^__version__ = "([^"]+)"$', source, re.MULTILINE)
    if not found:
        message = "keepsake/__init__.py declares no version"
        raise SystemExit(message)
    return found[1]


def run(*command: str) -> None:
    """Run a program, and stop the build if it fails.

    Python's user packages are hidden from it, or pip would take a package found
    there as installed and leave it out of the bundle.
    """
    alone = {**os.environ, "PYTHONNOUSERSITE": "1"}
    if subprocess.run(command, check=False, env=alone).returncode:
        message = f"{' '.join(command[:4])} failed"
        raise SystemExit(message)


def python_runtime() -> None:
    """Unpack Python from its NuGet package, the full one, with pip and venv."""
    cache = BUILD / "cache" / f"python-{PYTHON}.nupkg"
    if not cache.is_file():
        cache.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(PYTHON_URL, headers={"User-Agent": "keepsake-build"})
        with urllib.request.urlopen(request, timeout=120) as reply, cache.open("wb") as sink:
            shutil.copyfileobj(reply, sink)
    target = STAGE / "python"
    with zipfile.ZipFile(cache) as package:
        for member in package.namelist():
            if member.startswith("tools/") and not member.endswith("/"):
                where = target / member.removeprefix("tools/")
                where.parent.mkdir(parents=True, exist_ok=True)
                where.write_bytes(package.read(member))
    for part in UNUSED:
        shutil.rmtree(target / part, ignore_errors=True)
    python = str(target / "python.exe")
    pip = [python, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
    run(*pip, "--no-warn-script-location", "-r", str(ROOT / "requirements.txt"))


def app() -> None:
    """Copy the app and the starter, without caches."""
    target = STAGE / "app"
    for part in APP_PARTS:
        source = ROOT / part
        if source.is_dir():
            ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
            shutil.copytree(source, target / part, ignore=ignore)
        else:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target / part)
    shutil.copy2(ROOT / "packaging" / "keepsake.pyw", STAGE / "keepsake.pyw")


def licenses() -> None:
    """Gather the license of Python and of every package bundled beside it."""
    folder = STAGE / "licenses"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STAGE / "python" / "LICENSE.txt", folder / "Python.txt")
    for meta in sorted((STAGE / "python" / "Lib" / "site-packages").glob("*.dist-info")):
        name = meta.name.split("-")[0]
        texts = [
            path
            for path in meta.rglob("*")
            if path.is_file() and re.match(r"(LICEN[CS]E|COPYING|NOTICE)", path.name, re.IGNORECASE)
        ]
        if texts:
            joined = "\n\n".join(
                path.read_text(encoding="utf-8", errors="replace") for path in texts
            )
            (folder / f"{name}.txt").write_text(joined, encoding="utf-8", newline="\n")


def zip_app(release: str) -> Path:
    """Zip the app folder for installed copies to update from."""
    archive = DIST / f"keepsake-app-{release}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted((STAGE / "app").rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(STAGE / "app").as_posix())
    return archive


def installer(release: str) -> None:
    """Compile the installer with Inno Setup."""
    compiler = shutil.which("ISCC") or str(ISCC)
    script = ROOT / "packaging" / "keepsake.iss"
    run(
        compiler,
        "/Q",
        f"/DVersion={release}",
        f"/DStage={STAGE}",
        f"/O{DIST}",
        *sys.argv[1:],
        str(script),
    )


def main() -> None:
    """Build everything, from a clean stage."""
    release = version()
    shutil.rmtree(STAGE, ignore_errors=True)
    DIST.mkdir(parents=True, exist_ok=True)
    python_runtime()
    app()
    licenses()
    archive = zip_app(release)
    installer(release)
    sys.stdout.write(f"Built {archive.name} and KeepsakeSetup.exe in {DIST}\n")


if __name__ == "__main__":
    main()
