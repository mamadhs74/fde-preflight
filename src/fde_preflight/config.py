"""Manifest loading and validation (TOML, stdlib only)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ConfigError

# type -> required keys
REQUIRED: dict[str, tuple[str, ...]] = {
    "env": ("vars",),
    "dns": ("host",),
    "tcp": ("host", "port"),
    "tls": ("host",),
    "http": ("url",),
    "json": ("file",),
}


@dataclass(frozen=True)
class CheckSpec:
    type: str
    name: str
    params: dict[str, Any]


@dataclass(frozen=True)
class Manifest:
    title: str
    checks: tuple[CheckSpec, ...]


def parse(data: dict[str, Any]) -> Manifest:
    meta = data.get("meta", {})
    raw = data.get("check")
    if not isinstance(raw, list) or not raw:
        raise ConfigError("manifest needs at least one [[check]] table")

    specs: list[CheckSpec] = []
    for i, item in enumerate(raw, start=1):
        ctype = item.get("type")
        if ctype not in REQUIRED:
            raise ConfigError(
                f"check #{i}: unknown type {ctype!r} (expected one of {sorted(REQUIRED)})"
            )
        missing = [k for k in REQUIRED[ctype] if k not in item]
        if missing:
            raise ConfigError(f"check #{i} ({ctype}): missing required key(s) {missing}")
        params = {k: v for k, v in item.items() if k not in ("type", "name")}
        specs.append(CheckSpec(ctype, item.get("name", f"{ctype} #{i}"), params))
    return Manifest(title=meta.get("name", "Deployment preflight"), checks=tuple(specs))


def load(path: str | Path) -> Manifest:
    p = Path(path)
    try:
        with p.open("rb") as fh:
            data = tomllib.load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"manifest not found: {p}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {p}: {exc}") from exc
    return parse(data)
