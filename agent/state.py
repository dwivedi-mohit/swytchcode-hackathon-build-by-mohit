"""LedgerPilot agent state: Invoice, Decision, TraceEvent, InvoiceState."""
from __future__ import annotations

import threading
import time
from typing import Any, Literal, Optional, TypedDict

Label = Literal["OVERDUE", "DISPUTED", "DUE_SOON", "PAID"]
Action = Literal["paypal_chase", "jira_escalate", "log_only", "skip"]
Mode = Literal["write", "read_only"]
TraceStatus = Literal["ok", "pending_approval", "approved", "denied", "failed", "skipped", "seed"]

_SECRET_KEYS = ("authorization", "api_key", "apikey", "token", "secret", "password", "cookie")


def redact(value: Any) -> Any:
    """Recursively redact secret-looking values (SECURITY §6)."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in _SECRET_KEYS:
                out[k] = "***"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str) and value.lower().startswith("bearer "):
        return "Bearer ***"
    return value


class Invoice(TypedDict, total=False):
    id: str
    vendor: str
    amount: Optional[float]
    currency: str
    due_date: str
    status_hint: str
    email_ref: str
    raw_excerpt: str


class Decision(TypedDict):
    invoice_id: str
    label: Label
    action: Action
    reason: str


class TraceEvent(TypedDict, total=False):
    type: str  # "trace" | "approval" | "log" | "done" | "error"
    step: int
    node: str
    reasoning: str
    toolkit: str
    canonical_id: str
    request: dict
    response: dict
    decision: str
    status: TraceStatus
    ts: str
    # approval-only fields
    invoice_id: str
    request_hash: str


_step_counter = {"n": 0}
_step_lock = threading.Lock()


def next_step() -> int:
    with _step_lock:
        _step_counter["n"] += 1
        return _step_counter["n"]


def new_trace_event(
    node: str,
    reasoning: str = "",
    toolkit: str = "none",
    canonical_id: str = "",
    request: Optional[dict] = None,
    response: Optional[dict] = None,
    decision: str = "",
    status: str = "ok",
    etype: str = "trace",
    **extra: Any,
) -> TraceEvent:
    ev: TraceEvent = {
        "type": etype,
        "step": next_step(),
        "node": node,
        "reasoning": reasoning,
        "toolkit": toolkit,
        "canonical_id": canonical_id,
        "request": redact(request or {}),
        "response": redact(response or {}),
        "decision": decision,
        "status": status,  # type: ignore[typeddict-item]
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    ev.update(redact(extra))
    return ev


class InvoiceState(TypedDict, total=False):
    run_id: str
    prompt: str
    mode: Mode
    plan: list[str]
    invoices: list[Invoice]
    decisions: list[Decision]
    trace: list[TraceEvent]
    results: dict
    approval_pending: Optional[TraceEvent]
    final_answer: str
    errors: list[str]


def initial_state(prompt: str, run_id: str) -> InvoiceState:
    return {
        "run_id": run_id,
        "prompt": prompt,
        "mode": "write",
        "plan": [],
        "invoices": [],
        "decisions": [],
        "trace": [],
        "results": {},
        "approval_pending": None,
        "final_answer": "",
        "errors": [],
    }
