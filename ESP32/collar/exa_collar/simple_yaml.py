from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load YAML using PyYAML when present, with a small fallback parser.

    The fallback supports the subset used by this project: nested mappings,
    scalar values and inline lists. Installing PyYAML is still recommended.
    """

    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data or {}
    except ModuleNotFoundError:
        return _parse_subset(text)


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return {}
    if value.startswith("[") and value.endswith("]"):
        raw_items = value[1:-1].strip()
        if not raw_items:
            return []
        return [_parse_scalar(item.strip()) for item in raw_items.split(",")]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def _parse_subset(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = text.splitlines()

    for index, raw_line in enumerate(lines):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if stripped.startswith("- "):
            item_text = stripped[2:]
            if not isinstance(parent, list):
                raise ValueError(f"List item without list parent: {raw_line}")
            if ":" in item_text:
                key, value = item_text.split(":", 1)
                item = {key.strip(): _parse_scalar(value)}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(_parse_scalar(item_text))
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        parsed = _parse_scalar(value)

        if isinstance(parent, dict):
            if value == "":
                parsed = [] if _next_content_starts_list(lines, index) else {}
            parent[key] = parsed
            stack.append((indent, parsed))
        else:
            raise ValueError(f"Mapping entry inside list is not supported: {raw_line}")

    return root


def _next_content_starts_list(lines: list[str], index: int) -> bool:
    for raw_line in lines[index + 1 :]:
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        return line.strip().startswith("- ")
    return False
