from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Result, Status

_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def _get(obj: Any, dotted: str) -> tuple[bool, Any]:
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def check_json(name: str, p: dict[str, Any]) -> Result:
    """Validate a sample customer payload before building an integration on it.

    `required` is a list of dotted paths that must exist; `types` maps dotted
    paths to one of string/number/integer/boolean/array/object.
    """
    path = Path(p["file"])
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return Result(name, "json", Status.FAIL, f"file not found: {path}")
    except json.JSONDecodeError as exc:
        return Result(name, "json", Status.FAIL, f"invalid JSON: {exc}")

    problems: list[str] = []
    for key in p.get("required", []):
        if not _get(data, key)[0]:
            problems.append(f"missing {key}")
    for key, want in p.get("types", {}).items():
        found, val = _get(data, key)
        if not found:
            problems.append(f"missing {key}")
            continue
        expected = _TYPES.get(want)
        if expected is None:
            problems.append(f"unknown type {want!r} for {key}")
        elif not isinstance(val, expected) or (want != "boolean" and isinstance(val, bool)):
            problems.append(f"{key} is {type(val).__name__}, expected {want}")
    if problems:
        return Result(name, "json", Status.FAIL, "; ".join(problems),
                      details={"problems": problems})
    return Result(name, "json", Status.PASS, f"{path.name} matches expectations")
