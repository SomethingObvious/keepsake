# Contributing

The rules here are enforced by hooks, so set them up once:

```console
python -m pip install -r requirements-dev.txt
npm ci
winget install Gitleaks.Gitleaks
git config core.hooksPath .githooks
```

## Layout

| Where | What |
| --- | --- |
| `keepsake/` | The program, one module per concern, typed throughout |
| `ui/` | The window: `index.html`, `app.css`, and `app.js` type-checked against `types.d.ts` |
| `ERASER.md` | Remove Text: how `keepsake/eraser.py` snaps and fills, and what was measured |
| `tests/` | pytest, against a scratch data folder so nothing touches the real one |
| `scripts/lint.py` | Every check, in one command |
| `scripts/install.py` | Installs the self-updating copy and its shortcuts |
| `scripts/build.py`, `packaging/` | Build the installer and the app zip that installed copies update from |
| `docs/` | The website, served by GitHub Pages from main |
| `typings/` | Stubs for libraries that ship no types |

## Checks

`python scripts/lint.py` runs everything, and `--fast` runs the part pre-commit needs. Each tool runs at its strictest setting: Ruff with every rule, mypy `--strict` and basedpyright strict for Python, and TypeScript `strict`, typescript-eslint, Stylelint and html-validate for the window. Every version is pinned in `requirements-dev.txt` and `package-lock.json`, so what passes today still passes tomorrow.

Inline suppressions (`noqa`, `type: ignore`, `eslint-disable`, `@ts-ignore` and the rest) are rejected in every tracked file. A disagreement with a rule goes in that tool's config at the root, with its reason. Linter configs live at the root only, and there are no em dashes anywhere.

## Releasing

Every commit on main is a release, so `pre-push` takes one squashed commit that raises `__version__` in `keepsake/__init__.py` and passes every check. Fold a fix to unpushed work into its commit, and never force-push.

A checkout installed with `scripts/install.py` follows main and moves itself to each new version. A copy from `KeepsakeSetup.exe` follows the latest GitHub release instead and swaps the new app in on its next start. Both default to `%LOCALAPPDATA%\Programs\Keepsake`, so on a machine with a checkout copy, try the installer only as a test build (`python scripts/build.py /DTEST`, with `MSYS_NO_PATHCONV=1` in Git Bash).

To publish one, build it and attach both files to a release tagged with the version:

```console
python scripts/build.py
gh release create v1.0.0 dist/KeepsakeSetup.exe dist/keepsake-app-1.0.0.zip --title "Keepsake 1.0.0" --notes-file notes.md
```

Installed copies show each line of the notes that starts with `-` or `*`. Remove Text's two models are not in the installer or the app zip. Setup downloads them, pinned in `textremoval.FILES`: the overlay network from this repository at the tag in `textremoval.NETWORK_TAG`, and MI-GAN from Hugging Face at a fixed revision. A new network needs a new tag, and a new size and hash in `FILES`.

The site's screenshots are 1440 by 900 window captures with the frame cropped off, saved as WebP at 1600 and 960 pixels wide.
