"""Human-approval gate for value-moving calls (PayPal).

The agent blocks here until the operator clicks Approve/Deny in the UI,
or the timeout expires (SECURITY E7). Approval binds to the exact request
hash displayed on the card — approving a different request is impossible (X7).
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional


def request_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@dataclass
class PendingApproval:
    run_id: str
    invoice_id: str
    hash: str
    event: threading.Event = field(default_factory=threading.Event)
    decision: Optional[bool] = None  # True=approve, False=deny
    created: float = field(default_factory=time.time)


_pending: dict[str, PendingApproval] = {}
_lock = threading.Lock()


def create(run_id: str, invoice_id: str, payload: dict) -> PendingApproval:
    pa = PendingApproval(run_id=run_id, invoice_id=invoice_id, hash=request_hash(payload))
    with _lock:
        _pending[run_id] = pa
    return pa


def resolve(run_id: str, invoice_id: str, approved: bool, hash: str) -> tuple[bool, str]:
    """Called by the API on Approve/Deny. Validates request hash (X7)."""
    with _lock:
        pa = _pending.get(run_id)
    if pa is None:
        return False, "no approval pending for this run"
    if pa.invoice_id != invoice_id:
        return False, "invoice mismatch"
    if pa.hash != hash:
        return False, "approval does not match the displayed request"
    if pa.event.is_set():
        return False, "approval already resolved"
    pa.decision = approved
    pa.event.set()
    return True, "approved" if approved else "denied"


def wait(pa: PendingApproval, timeout_s: float) -> tuple[bool, str]:
    """Block until resolved. Returns (approved, how). AUTO_APPROVE for tests."""
    if os.getenv("AUTO_APPROVE", "0") == "1":
        pa.decision = True
        pa.event.set()
        return True, "auto"
    ok = pa.event.wait(timeout=timeout_s)
    with _lock:
        _pending.pop(pa.run_id, None)
    if not ok:
        return False, "timeout"
    return bool(pa.decision), "approved" if pa.decision else "denied"


def get(run_id: str) -> Optional[PendingApproval]:
    with _lock:
        return _pending.get(run_id)


def clear(run_id: str) -> None:
    with _lock:
        _pending.pop(run_id, None)
