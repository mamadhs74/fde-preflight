from __future__ import annotations

import os
from typing import Any

from ..models import Result, Status


def check_env(name: str, p: dict[str, Any]) -> Result:
    """Required environment variables must be set and non-empty.

    Values are never included in output, only the variable names, so reports are
    safe to paste into a customer ticket.
    """
    names: list[str] = list(p["vars"])
    missing = [v for v in names if not os.environ.get(v)]
    if missing:
        return Result(name, "env", Status.FAIL, f"missing: {', '.join(missing)}",
                      details={"missing": missing})
    return Result(name, "env", Status.PASS, f"{len(names)} variable(s) set")
