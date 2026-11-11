import json

import pytest

from fde_preflight import config
from fde_preflight.cli import main
from fde_preflight.models import ConfigError, Report, Result, Status
from fde_preflight.report import to_markdown, to_text


def _manifest(tmp_path, body: str):
    p = tmp_path / "m.toml"
    p.write_text(body)
    return str(p)


def test_config_rejects_unknown_type():
    with pytest.raises(ConfigError, match="unknown type"):
        config.parse({"check": [{"type": "ftp"}]})


def test_config_rejects_missing_keys():
    with pytest.raises(ConfigError, match="missing required"):
        config.parse({"check": [{"type": "tcp", "host": "x"}]})


def test_config_requires_checks():
    with pytest.raises(ConfigError):
        config.parse({})


def test_cli_ready_exit_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FOO", "1")
    path = _manifest(tmp_path, '[[check]]\ntype="env"\nvars=["FOO"]\n')
    assert main([path]) == 0
    assert "READY" in capsys.readouterr().out


def test_cli_failure_exit_one_and_json(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("NOPE_X", raising=False)
    path = _manifest(tmp_path, '[[check]]\ntype="env"\nvars=["NOPE_X"]\n')
    assert main([path, "-f", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ready"] is False and data["counts"]["fail"] == 1


def test_cli_bad_manifest_exit_two(tmp_path, capsys):
    assert main([str(tmp_path / "missing.toml")]) == 2
    assert "error:" in capsys.readouterr().err


def test_cli_output_file(tmp_path, monkeypatch):
    monkeypatch.setenv("FOO", "1")
    path = _manifest(tmp_path, '[[check]]\ntype="env"\nvars=["FOO"]\n')
    out = tmp_path / "r.md"
    assert main([path, "-f", "markdown", "-o", str(out)]) == 0
    assert out.read_text().startswith("# ")


def test_only_filter(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("NOPE_X", raising=False)
    path = _manifest(tmp_path, '[[check]]\ntype="env"\nvars=["NOPE_X"]\n'
                               '[[check]]\ntype="tcp"\nhost="127.0.0.1"\nport=1\ntimeout=1\n')
    assert main([path, "--only", "env", "-f", "json"]) == 1
    assert len(json.loads(capsys.readouterr().out)["results"]) == 1


def test_warnings_do_not_fail():
    rep = Report("t", (Result("a", "http", Status.WARN, "slow"),))
    assert rep.exit_code == 0
    assert "READY" in to_text(rep)


def test_markdown_escapes_pipes():
    rep = Report("t", (Result("a", "env", Status.FAIL, "x|y"),))
    assert "x\\|y" in to_markdown(rep)
