"""Shared node helpers: record trace events onto state + the live event bus."""
from __future__ import annotations

from typing import Any

from ..events import bus
from ..state import InvoiceState, TraceEvent


def record(state: InvoiceState, ev: TraceEvent) -> TraceEvent:
    state.setdefault("trace", []).append(ev)
    bus.publish(state.get("run_id", ""), ev)
    return ev


def add_error(state: InvoiceState, msg: str) -> None:
    errs = state.setdefault("errors", [])
    if msg not in errs:
        errs.append(msg)


def emit_log(state: InvoiceState, text: str, level: str = "info") -> None:
    bus.publish(
        state.get("run_id", ""),
        {"type": "log", "level": level, "text": text, "ts": _ts()},
    )


def _ts() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def env_int(name: str, default: int) -> int:
    import os

    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def as_dicts(items: Any) -> list:
    if isinstance(items, list):
        return [i for i in items if isinstance(i, dict)]
    return []
