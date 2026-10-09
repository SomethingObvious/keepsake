"""Every check this repository has, in one command.

    python scripts/lint.py          everything: what pre-push and CI run
    python scripts/lint.py --fast   formatting, lint, spelling, secrets and policy: pre-commit

Each tool runs at the strictest setting it has, configured at the repository's
root and nowhere else. Three policies are enforced here rather than by a tool:

* No inline suppressions. A disagreement with a rule is argued in that rule's
    config, with its reason, where everyone can see it; a comment beside the
    line is a suppression nobody reviews. (After afterimage and Overseer.)
* No hidden configs. A linter config in a subfolder quietly weakens the root
    one for everything under it.
* No em dashes, after afterimage: they are the house style of machine prose.
"""

import json
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
TEXT = frozenset(
    {
        ".py",
        ".pyi",
        ".pyw",
        ".js",
        ".mjs",
        ".ts",
        ".css",
        ".html",
        ".json",
        ".md",
        ".toml",
        ".yml",
        ".yaml",
        ".txt",
        ".cfg",
        ".ini",
        "",
    }
)
# Only this file and CONTRIBUTING.md, which lists them, may name a suppression.
SUPPRESSION_ALLOWED = frozenset({"scripts/lint.py", "CONTRIBUTING.md"})
SUPPRESSION = re.compile(
    r"noqa|type:\s*ignore|pyright:\s*(?:ignore|basic|strict)|mypy:\s*ignore|eslint-disable"
    r"|@ts-(?:ignore|expect-error|nocheck)|stylelint-disable|markdownlint-(?:disable|enable"
    r"|capture|restore|configure)|shellcheck\s+disable|yamllint\s+disable|html-validate-disable"
    r"|gitleaks:allow|typos:\s*(?:ignore|off)|pragma:\s*no\s*cover",
    re.IGNORECASE,
)
CONFIG_NAMES = re.compile(
    r"^(?:ruff\.toml|\.ruff\.toml|pyproject\.toml|setup\.cfg|mypy\.ini|\.mypy\.ini"
    r"|pyrightconfig\.json|\.eslintrc.*|eslint\.config\..*|tsconfig.*\.json|\.stylelintrc.*"
    r"|stylelint\.config\..*|\.htmlvalidate.*|\.markdownlint.*|\.yamllint.*|typos\.toml"
    r"|\.typos\.toml|\.editorconfig|\.prettierrc.*)$",
)
EM_DASH = "—"


@dataclass(frozen=True)
class Check:
    """One named check: a command to run, or a function for the policies."""

    name: str
    fast: bool
    command: Callable[[], list[str]] | None = None
    policy: Callable[[], list[str]] | None = None


def tracked() -> list[Path]:
    """Return every tracked file, as a path."""
    listing = subprocess.run(
        [git(), "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    return [ROOT / name for name in listing.split("\0") if name]


def texts() -> list[tuple[str, str]]:
    """Return every tracked text file's name and contents."""
    found: list[tuple[str, str]] = []
    for path in tracked():
        if path.suffix.lower() in TEXT and path.is_file():
            name = path.relative_to(ROOT).as_posix()
            found.append((name, path.read_text(encoding="utf-8", errors="replace")))
    return found


def no_suppressions() -> list[str]:
    """Return every inline lint suppression in a tracked file."""
    return [
        f"{name}:{number}: {line.strip()}"
        for name, text in texts()
        if name not in SUPPRESSION_ALLOWED
        for number, line in enumerate(text.splitlines(), 1)
        if SUPPRESSION.search(line)
    ]


def no_hidden_configs() -> list[str]:
    """Return every linter config below the repository's root."""
    return [
        path.relative_to(ROOT).as_posix()
        for path in tracked()
        if path.parent != ROOT and CONFIG_NAMES.match(path.name)
    ]


def no_em_dashes() -> list[str]:
    """Return every line with an em dash in it."""
    return [
        f"{name}:{number}"
        for name, text in texts()
        if name != "scripts/lint.py"
        for number, line in enumerate(text.splitlines(), 1)
        if EM_DASH in line
    ]


def git() -> str:
    """Return the git program."""
    return shutil.which("git") or "git"


def program(name: str) -> str:
    """Return an installed program's full path, or stop with how to install it."""
    found = shutil.which(name)
    if not found:
        message = f"{name} is missing: pip install -r requirements-dev.txt, or see CONTRIBUTING.md"
        raise SystemExit(message)
    return found


def node_tool(package: str, command: str) -> list[str]:
    """Return how to run a command from an installed node package, without npx or a shell."""
    manifest = ROOT / "node_modules" / package / "package.json"
    if not manifest.is_file():
        message = f"{package} is not installed: npm ci"
        raise SystemExit(message)
    bins = json.loads(manifest.read_text(encoding="utf-8"))["bin"]
    script = bins if isinstance(bins, str) else bins[command]
    return [program("node"), str(manifest.parent / script)]


def module(name: str, *args: str) -> Callable[[], list[str]]:
    """Return a check that runs a Python module."""
    return lambda: [PYTHON, "-m", name, *args]


def node(package: str, command: str, *args: str) -> Callable[[], list[str]]:
    """Return a check that runs a node package's command."""
    return lambda: [*node_tool(package, command), *args]


def binary(name: str, *args: str) -> Callable[[], list[str]]:
    """Return a check that runs an installed program."""
    return lambda: [program(name), *args]


def hooks() -> list[str]:
    """Return the git hooks, which are shell scripts."""
    return [str(p) for p in sorted((ROOT / ".githooks").iterdir()) if not p.suffix]


CHECKS = (
    Check("ruff format", fast=True, command=module("ruff", "format", "--check", ".")),
    Check("ruff", fast=True, command=module("ruff", "check", ".")),
    Check("typos", fast=True, command=binary("typos")),
    Check(
        "gitleaks",
        fast=True,
        command=binary(
            "gitleaks", "dir", ".", "--no-banner", "--redact", "--config", ".gitleaks.toml"
        ),
    ),
    Check("no inline suppressions", fast=True, policy=no_suppressions),
    Check("no hidden configs", fast=True, policy=no_hidden_configs),
    Check("no em dashes", fast=True, policy=no_em_dashes),
    Check("mypy --strict", fast=False, command=module("mypy")),
    Check("basedpyright strict", fast=False, command=binary("basedpyright")),
    Check("pytest", fast=False, command=module("pytest", "-q")),
    Check("tsc --strict", fast=False, command=node("typescript", "tsc", "-p", "tsconfig.json")),
    Check("eslint", fast=False, command=node("eslint", "eslint", "--max-warnings=0", ".")),
    Check(
        "stylelint",
        fast=False,
        command=node("stylelint", "stylelint", "ui/**/*.css", "docs/**/*.css"),
    ),
    Check(
        "html-validate",
        fast=False,
        command=node("html-validate", "html-validate", "ui/index.html", "docs/index.html"),
    ),
    Check(
        "markdownlint",
        fast=False,
        command=node(
            "markdownlint-cli2", "markdownlint-cli2", "**/*.md", "#node_modules", "#build", "#dist"
        ),
    ),
    Check("yamllint", fast=False, command=module("yamllint", "--strict", ".")),
    Check("editorconfig", fast=False, command=binary("ec")),
    Check("shellcheck", fast=False, command=lambda: [program("shellcheck"), *hooks()]),
)


def run(check: Check) -> tuple[bool, str]:
    """Run one check and return whether it passed, and what it said if it did not."""
    if check.policy is not None:
        found = check.policy()
        return not found, "\n".join(found)
    if check.command is None:
        return True, ""
    result = subprocess.run(
        check.command(),
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def say(text: str) -> None:
    """Print, as UTF-8 whatever the console: a tool's complaint can quote any character."""
    sys.stdout.buffer.write(text.encode("utf-8", "replace"))
    sys.stdout.buffer.flush()


def main(argv: list[str]) -> int:
    """Run the checks and report each; fail if any failed."""
    fast = "--fast" in argv
    failed: list[str] = []
    for check in CHECKS:
        if fast and not check.fast:
            continue
        started = time.perf_counter()
        passed, said = run(check)
        took = time.perf_counter() - started
        say(f"{'pass' if passed else 'FAIL'}  {check.name}  ({took:.1f}s)\n")
        if not passed:
            failed.append(check.name)
            say("\n".join(f"      {line}" for line in said.splitlines()[-60:]) + "\n")
    if failed:
        say(f"\n{len(failed)} failed: {', '.join(failed)}\n")
        return 1
    say("\nEverything passed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
