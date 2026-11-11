"""Run checks concurrently, never letting one broken check abort the run."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from .checks import REGISTRY
from .config import CheckSpec, Manifest
from .models import Report, Result, Status


def _run_one(spec: CheckSpec) -> Result:
    start = time.perf_counter()
    try:
        result = REGISTRY[spec.type](spec.name, spec.params)
    except Exception as exc:  # a check bug must surface as a failure, not a crash
        result = Result(spec.name, spec.type, Status.FAIL,
                        f"check crashed: {type(exc).__name__}: {exc}")
    elapsed = (time.perf_counter() - start) * 1000
    return Result(result.name, result.type, result.status, result.message,
                  round(elapsed, 1), result.details)


def run(manifest: Manifest, workers: int = 8, only: set[str] | None = None) -> Report:
    specs = [s for s in manifest.checks if not only or s.type in only]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = tuple(pool.map(_run_one, specs))  # map preserves manifest order
    return Report(manifest.title, results)
