# fde-preflight

[![CI](https://github.com/mamadhs74/fde-preflight/actions/workflows/ci.yml/badge.svg)](https://github.com/mamadhs74/fde-preflight/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![deps](https://img.shields.io/badge/dependencies-0-brightgreen)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

**Is the customer's environment actually ready for go-live?** One manifest, one command, one report you can paste into a ticket.

Forward-deployed engineers lose days to the same avoidable blockers: a missing credential, a firewall rule that was never opened, a certificate that expires next week, a sample payload that doesn't match the spec. `fde-preflight` turns that checklist into a repeatable, version-controlled run.

Illustrative output of a run with a missing credential and a slow endpoint:

```text
$ fde-preflight examples/acme.toml
Acme Corp: production go-live preflight
=======================================
[FAIL] Credentials present         missing: ACME_API_KEY
[PASS] API hostname resolves       example.com -> 2600:1406:..., 93.184.215.14
[PASS] HTTPS port reachable        example.com:443 open (24 ms)
[PASS] Certificate healthy         valid, 212 days left (TLSv1.3)
[WARN] Health endpoint             200 but slow: 1730 ms > 1500 ms
[PASS] Sample order payload shape  sample_order.json matches expectations

NOT READY: 4 passed, 1 warning(s), 1 failed
```

## Install

```bash
pip install git+https://github.com/mamadhs74/fde-preflight
```

Requires Python 3.11+. No third-party runtime dependencies.

## Usage

```bash
fde-preflight manifest.toml                    # human-readable
fde-preflight manifest.toml -f json            # for CI / dashboards
fde-preflight manifest.toml -f markdown -o report.md   # hand to the customer
fde-preflight manifest.toml --only tls --only dns      # subset
```

Exit codes: `0` ready (warnings allowed), `1` at least one failure, `2` bad manifest.

## Checks

| type | verifies | key options |
|------|----------|-------------|
| `env` | variables are set (values never printed) | `vars` |
| `dns` | hostname resolves | `host` |
| `tcp` | port is reachable through firewalls | `host`, `port`, `timeout` |
| `tls` | verified handshake and expiry runway | `host`, `port`, `warn_days`, `min_days` |
| `http` | status, latency budget, body substring | `url`, `expect_status`, `max_latency_ms`, `contains`, `headers` |
| `json` | sample payload has required paths and types | `file`, `required`, `types` |

Header values support `${ENV_VAR}` expansion, so secrets never live in the manifest.

See [`examples/acme.toml`](examples/acme.toml) for a complete manifest.

## Design notes

- **Warnings don't block.** Slow or expiring-soon is a conversation; broken is a blocker. Only failures change the exit code.
- **One bad check never aborts the run.** Checks run concurrently and an unexpected exception is reported as a failure of that check.
- **Safe to share.** Reports contain variable names and statuses, never secret values.
- **Zero dependencies.** Standard library only, so it installs cleanly on locked-down customer machines.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

Adding a check: write `check_x(name, params) -> Result` in `src/fde_preflight/checks/`, register it in `checks/__init__.py`, and list its required keys in `config.REQUIRED`.

## License

MIT
