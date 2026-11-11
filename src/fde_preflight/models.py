"""Core data types shared by checks, runner and reporters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True)
class Result:
    name: str
    type: str
    status: Status
    message: str
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass(frozen=True)
class Report:
    title: str
    results: tuple[Result, ...]

    @property
    def counts(self) -> dict[str, int]:
        out = {s.value: 0 for s in Status}
        for r in self.results:
            out[r.status.value] += 1
        return out

    @property
    def exit_code(self) -> int:
        """0 = ready, 1 = failures present, warnings alone do not fail the run."""
        return 1 if self.counts["fail"] else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "counts": self.counts,
            "ready": self.exit_code == 0,
            "results": [r.to_dict() for r in self.results],
        }


class ConfigError(ValueError):
    """Raised when a manifest is malformed."""
