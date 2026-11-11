from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

from ..models import Result, Status

_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)\}")


def expand_env(value: str) -> str:
    """Replace ${VAR} with environment values so secrets stay out of manifests."""
    return _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)


def check_http(name: str, p: dict[str, Any]) -> Result:
    """GET a URL; assert status, latency budget and optional body substring.

    Latency above `max_latency_ms` is a warning, not a failure: slow is a
    conversation, broken is a blocker.
    """
    url = p["url"]
    expect = int(p.get("expect_status", 200))
    budget = p.get("max_latency_ms")
    timeout = float(p.get("timeout", 10))
    headers = {k: expand_env(str(v)) for k, v in p.get("headers", {}).items()}
    headers.setdefault("User-Agent", "fde-preflight/0.1")

    req = urllib.request.Request(url, headers=headers, method=p.get("method", "GET"))
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, body = resp.status, resp.read(1_000_000)
    except urllib.error.HTTPError as exc:
        status, body = exc.code, exc.read(1_000_000)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return Result(name, "http", Status.FAIL, f"request failed: {getattr(exc, 'reason', exc)}")
    ms = (time.perf_counter() - start) * 1000
    details = {"status_code": status, "latency_ms": round(ms, 1)}

    if status != expect:
        return Result(name, "http", Status.FAIL, f"expected {expect}, got {status}",
                      ms, details)
    needle = p.get("contains")
    if needle and needle.encode() not in body:
        return Result(name, "http", Status.FAIL, f"body missing {needle!r}", ms, details)
    if budget is not None and ms > float(budget):
        return Result(name, "http", Status.WARN,
                      f"{status} but slow: {ms:.0f} ms > {float(budget):.0f} ms", ms, details)
    return Result(name, "http", Status.PASS, f"{status} in {ms:.0f} ms", ms, details)
