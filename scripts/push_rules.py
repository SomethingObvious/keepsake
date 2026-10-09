"""What a push to main must be: one squashed commit that raises the version.

Every commit on main is a release the installed copies move to, so history
holds big updates only. Work is squashed into one commit before it is pushed
(git reset --soft on the remote's commit, then commit again); published
history is never rewritten, so this is the last place squashing can happen.
pre-push hands over one line per ref on stdin.
"""

import re
import shutil
import subprocess
import sys

NO_COMMIT = "0" * 40
MAIN = "refs/heads/main"
VERSION = re.compile(r'^__version__ = "(\d+)\.(\d+)\.(\d+)"$', re.MULTILINE)


def git(*args: str) -> str:
    """Return what a git command printed, or "" if it failed."""
    done = subprocess.run(
        [shutil.which("git") or "git", *args], capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else ""


def version(commit: str) -> tuple[int, ...] | None:
    """Return the version a commit carries."""
    found = VERSION.search(git("show", f"{commit}:keepsake/__init__.py"))
    return tuple(int(part) for part in found.groups()) if found else None


def problem(line: str) -> str:
    """Return what is wrong with pushing one ref, or "" if nothing is."""
    parts = line.split()
    if len(parts) != len(("local ref", "local sha", "remote ref", "remote sha")):
        return ""
    _, local, remote_ref, remote = parts
    if local == NO_COMMIT or remote_ref != MAIN or remote == NO_COMMIT:
        return ""  # a deletion, another ref, or the very first push
    count = int(git("rev-list", "--count", f"{remote}..{local}").strip() or "0")
    if count > 1:
        return (
            f"This push holds {count} commits; main takes one per update. Squash them:\n"
            f"  git reset --soft {remote[:12]} && git commit"
        )
    new, old = version(local), version(remote)
    if new is None or old is None or new <= old:
        return "Raise __version__ in keepsake/__init__.py: every commit on main is a release."
    return ""


def main() -> int:
    """Refuse the push if any ref breaks a rule."""
    found = [message for line in sys.stdin.read().splitlines() if (message := problem(line))]
    for message in found:
        sys.stderr.write(message + "\n")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
