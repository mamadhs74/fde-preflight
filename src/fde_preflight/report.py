"""Renderers: terminal text, JSON (for CI) and Markdown (to hand to a customer)."""

from __future__ import annotations

import json

from .models import Report, Status

_ICON = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL", Status.SKIP: "SKIP"}
_EMOJI = {Status.PASS: "✅", Status.WARN: "⚠️", Status.FAIL: "❌", Status.SKIP: "⏭️"}


def _summary(report: Report) -> str:
    c = report.counts
    verdict = "READY" if report.exit_code == 0 else "NOT READY"
    return f"{verdict}: {c['pass']} passed, {c['warn']} warning(s), {c['fail']} failed"


def to_text(report: Report) -> str:
    width = max((len(r.name) for r in report.results), default=0)
    lines = [report.title, "=" * len(report.title)]
    for r in report.results:
        lines.append(f"[{_ICON[r.status]}] {r.name.ljust(width)}  {r.message}")
    lines += ["", _summary(report)]
    return "\n".join(lines)


def to_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2)


def to_markdown(report: Report) -> str:
    lines = [f"# {report.title}", "", f"**{_summary(report)}**", "",
             "| | Check | Type | Result | Time |", "|---|---|---|---|---|"]
    for r in report.results:
        msg = r.message.replace("|", "\\|")
        lines.append(
            f"| {_EMOJI[r.status]} | {r.name} | `{r.type}` | {msg} | {r.duration_ms:.0f} ms |"
        )
    return "\n".join(lines)


RENDERERS = {"text": to_text, "json": to_json, "markdown": to_markdown}
