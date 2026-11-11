"""Check implementations. Each takes (name, params) and returns a Result."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..models import Result
from .env import check_env
from .http import check_http
from .jsonfile import check_json
from .net import check_dns, check_tcp, check_tls

CheckFn = Callable[[str, dict[str, Any]], Result]

REGISTRY: dict[str, CheckFn] = {
    "env": check_env,
    "dns": check_dns,
    "tcp": check_tcp,
    "tls": check_tls,
    "http": check_http,
    "json": check_json,
}
