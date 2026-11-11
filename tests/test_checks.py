import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from fde_preflight.checks.env import check_env
from fde_preflight.checks.http import check_http, expand_env
from fde_preflight.checks.jsonfile import check_json
from fde_preflight.checks.net import check_tcp, days_until
from fde_preflight.models import Status


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/missing":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"hello ok")

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", srv.server_port
    srv.shutdown()


def test_env_reports_names_only(monkeypatch):
    monkeypatch.setenv("A_SET", "secret-value")
    monkeypatch.delenv("B_UNSET", raising=False)
    r = check_env("e", {"vars": ["A_SET", "B_UNSET"]})
    assert r.status is Status.FAIL
    assert "B_UNSET" in r.message and "secret-value" not in r.message


def test_env_pass(monkeypatch):
    monkeypatch.setenv("A_SET", "x")
    assert check_env("e", {"vars": ["A_SET"]}).status is Status.PASS


def test_http_pass_and_contains(server):
    url, _ = server
    assert check_http("h", {"url": url, "contains": "ok"}).status is Status.PASS
    assert check_http("h", {"url": url, "contains": "nope"}).status is Status.FAIL


def test_http_wrong_status(server):
    url, _ = server
    r = check_http("h", {"url": url + "/missing"})
    assert r.status is Status.FAIL and "404" in r.message


def test_http_slow_is_warning(server):
    url, _ = server
    assert check_http("h", {"url": url, "max_latency_ms": 0}).status is Status.WARN


def test_http_unreachable():
    r = check_http("h", {"url": "http://127.0.0.1:1", "timeout": 1})
    assert r.status is Status.FAIL


def test_expand_env(monkeypatch):
    monkeypatch.setenv("TOK", "abc")
    assert expand_env("Bearer ${TOK}") == "Bearer abc"


def test_tcp(server):
    _, port = server
    assert check_tcp("t", {"host": "127.0.0.1", "port": port}).status is Status.PASS
    assert check_tcp("t", {"host": "127.0.0.1", "port": 1, "timeout": 1}).status is Status.FAIL


def test_days_until():
    now = datetime(2030, 1, 1, tzinfo=UTC)
    future = (now + timedelta(days=10)).strftime("%b %d %H:%M:%S %Y GMT")
    assert days_until(future, now) == pytest.approx(10, abs=0.01)


def test_json_checks(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"id": 1, "c": {"email": "a@b"}, "ok": True}))
    good = check_json("j", {"file": str(f), "required": ["c.email"],
                            "types": {"id": "integer", "ok": "boolean"}})
    assert good.status is Status.PASS
    bad = check_json("j", {"file": str(f), "required": ["c.phone"], "types": {"id": "string"}})
    assert bad.status is Status.FAIL and "c.phone" in bad.message


def test_json_bool_is_not_integer(tmp_path):
    f = tmp_path / "p.json"
    f.write_text('{"n": true}')
    assert check_json("j", {"file": str(f), "types": {"n": "integer"}}).status is Status.FAIL


def test_json_bad_file(tmp_path):
    assert check_json("j", {"file": str(tmp_path / "nope.json")}).status is Status.FAIL
    f = tmp_path / "bad.json"
    f.write_text("{")
    assert check_json("j", {"file": str(f)}).status is Status.FAIL
