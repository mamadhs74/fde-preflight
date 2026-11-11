"""Command-line entry point.

Exit codes: 0 ready, 1 one or more checks failed, 2 bad manifest / usage.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__, config, report, runner
from .checks import REGISTRY
from .models import ConfigError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fde-preflight",
        description="Verify a customer environment is ready before go-live.",
    )
    p.add_argument("manifest", help="path to a preflight TOML manifest")
    p.add_argument("-f", "--format", choices=sorted(report.RENDERERS), default="text")
    p.add_argument("-o", "--output", help="write the report to a file instead of stdout")
    p.add_argument("--only", action="append", choices=sorted(REGISTRY),
                   help="run only this check type (repeatable)")
    p.add_argument("--workers", type=int, default=8, help="concurrent checks (default 8)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = config.load(args.manifest)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rep = runner.run(manifest, workers=args.workers, only=set(args.only or []))
    rendered = report.RENDERERS[args.format](rep)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rendered + "\n")
    else:
        print(rendered)
    return rep.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
