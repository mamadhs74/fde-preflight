from __future__ import annotations

import socket
import ssl
import time
from datetime import UTC, datetime
from typing import Any

from ..models import Result, Status


def check_dns(name: str, p: dict[str, Any]) -> Result:
    host = p["host"]
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        return Result(name, "dns", Status.FAIL, f"{host} does not resolve: {exc}")
    addrs = sorted({i[4][0] for i in infos})
    return Result(name, "dns", Status.PASS, f"{host} -> {', '.join(addrs[:3])}",
                  details={"addresses": addrs})


def check_tcp(name: str, p: dict[str, Any]) -> Result:
    host, port = p["host"], int(p["port"])
    timeout = float(p.get("timeout", 5))
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        return Result(name, "tcp", Status.FAIL, f"{host}:{port} unreachable: {exc}")
    ms = (time.perf_counter() - start) * 1000
    return Result(name, "tcp", Status.PASS, f"{host}:{port} open ({ms:.0f} ms)",
                  details={"connect_ms": round(ms, 1)})


def days_until(not_after: str, now: datetime | None = None) -> float:
    """Days until a certificate's notAfter string (e.g. 'Jun  1 12:00:00 2030 GMT')."""
    expiry = datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), tz=UTC)
    return (expiry - (now or datetime.now(UTC))).total_seconds() / 86400


def check_tls(name: str, p: dict[str, Any]) -> Result:
    """Handshake with full verification; warn when expiry is close.

    `min_days` is the failure threshold (default 7); `warn_days` the warning
    threshold (default 30).
    """
    host, port = p["host"], int(p.get("port", 443))
    timeout = float(p.get("timeout", 5))
    fail_days = float(p.get("min_days", 7))
    warn_days = float(p.get("warn_days", 30))
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as raw, \
                ctx.wrap_socket(raw, server_hostname=host) as tls:
            cert = tls.getpeercert()
            version = tls.version()
    except ssl.SSLCertVerificationError as exc:
        return Result(name, "tls", Status.FAIL, f"certificate rejected: {exc.verify_message}")
    except (OSError, ssl.SSLError) as exc:
        return Result(name, "tls", Status.FAIL, f"{host}:{port} handshake failed: {exc}")

    left = days_until(cert["notAfter"])
    details = {"days_left": round(left, 1), "protocol": version}
    if left < fail_days:
        return Result(name, "tls", Status.FAIL, f"certificate expires in {left:.0f} days",
                      details=details)
    if left < warn_days:
        return Result(name, "tls", Status.WARN, f"certificate expires in {left:.0f} days",
                      details=details)
    return Result(name, "tls", Status.PASS, f"valid, {left:.0f} days left ({version})",
                  details=details)
