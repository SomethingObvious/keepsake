"""JSON files in the data folder, written so a crash never leaves half of one."""

import json
from pathlib import Path
from typing import cast


def load(path: Path, fallback: object) -> object:
    """Return the JSON in `path`, or `fallback` when it is missing or damaged."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def save(path: Path, value: object) -> None:
    """Write JSON beside the target and swap it in, so a reader never sees a torn file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=1), encoding="utf-8")
    temporary.replace(path)


def record(value: object) -> dict[str, object]:
    """Return a JSON object as a typed record, or an empty one when it is not an object."""
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in cast("dict[object, object]", value).items()}


def items(value: object) -> list[object]:
    """Return a JSON array as a typed list, or an empty one when it is not an array."""
    return list(cast("list[object]", value)) if isinstance(value, list) else []


def is_object(value: object) -> bool:
    """Return whether a JSON value is an object."""
    return isinstance(value, dict)


def load_list(path: Path) -> list[dict[str, object]]:
    """Return a stored list of records, dropping anything that is not one."""
    return [record(item) for item in items(load(path, [])) if is_object(item)]
