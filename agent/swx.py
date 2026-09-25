"""The single choke point for every external call (TECHNICAL_ARCHITECTURE §3).

Live path  : Swytchcode Runtime SDK if installed+authenticated, else `swy` CLI.
Mock path  : deterministic fake responses — MOCK_SWX=1, no SDK, or no auth.
             Keeps Gates C/D green with zero credentials (BUILD.md §4.1).

Writes carry an idempotency key (run_id:invoice_id) — re-running a prompt can
never double-chase (SECURITY E10). Retry-once for transient failures (E5).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import zlib
from typing import Any, Optional

from . import approvals  # noqa: F401  (keeps import graph simple for tooling)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def mode() -> str:
    """'mock' | 'live'"""
    if _env("SWX_MODE") == "mock" or _env("MOCK_SWX") == "1":
        return "mock"
    if _env("SWX_MODE") == "live":
        return "live"
    return "live" if (_sdk_available() or _cli_present()) else "mock"


def _sdk_available() -> bool:
    try:  # pragma: no cover - depends on local install
        import swytchcode_runtime  # noqa: F401

        return True
    except Exception:
        return False


def _stable(prefix: str, seed: str, n: int = 8) -> str:
    return f"{prefix}{zlib.crc32(seed.encode()) % (10 ** n):0{n}d}"


def _mock_execute(canonical_id: str, params: dict, invoice_id: str) -> dict:
    if canonical_id == "gmail.messages.list":
        return {"messages": [{"id": f"msg-{i}"} for i in range(1, 5)], "resultSizeEstimate": 4}
    if canonical_id == "gmail.messages.get":
        return {"id": params.get("id"), "subject": "Invoice", "snippet": ""}
    if canonical_id.startswith("paypal."):
        pid = _stable("INV-", f"{invoice_id}:{canonical_id}", 4).upper()
        return {"id": pid, "status": "SENT", "amount": params.get("invoice", {}).get("amount", {})}
    if canonical_id == "jira.issues.create":
        key = _stable("OPS-", invoice_id or canonical_id, 4)
        return {"key": key, "id": key.replace("OPS-", "")}
    if canonical_id == "notion.databases.query":
        return {"results": []}
    if canonical_id == "notion.pages.create":
        return {"page_id": _stable("notion-page-", invoice_id or canonical_id, 10)}
    if canonical_id == "slack.chat.postMessage":
        return {"ok": True, "channel": "#finance-ops", "ts": f"{time.time():.6f}"}
    return {"ok": True, "echo": canonical_id}


_idempotency_store: dict[str, dict] = {}


def execute(
    canonical_id: str,
    params: dict,
    run_id: str = "",
    invoice_id: str = "",
    write: bool = False,
) -> dict:
    """Execute one Swytchcode tool call. Never raises — returns
    {"ok": bool, "body": dict, "error": str, "mode": str} (SECURITY §4)."""
    key = f"{run_id}:{invoice_id}:{canonical_id}" if write else ""
    if key and key in _idempotency_store:  # E10 — replay, no second side effect
        return {"ok": True, "body": _idempotency_store[key], "mode": "idempotent", "error": ""}

    if mode() == "mock":
        body = _mock_execute(canonical_id, params, invoice_id)
        if key:
            _idempotency_store[key] = body
        return {"ok": True, "body": body, "mode": "mock", "error": ""}

    args = {k: v for k, v in params.items()
            if k.lower() not in ("authorization", "idempotency-key", "params")}
    # nested {"params": {...}} envelopes (doc §2 example) are unwrapped
    if isinstance(params.get("params"), dict):
        args.update(params["params"])
    headers: dict[str, str] = {}
    if write and key:
        headers["Idempotency-Key"] = key  # E10 — carried as a request header
    last_error = ""
    for attempt in (1, 2):  # one automatic retry for transient failures (E5)
        try:
            body = _live_execute(canonical_id, args, headers)
            if key:
                _idempotency_store[key] = body
            return {"ok": True, "body": body, "mode": "live", "error": ""}
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt == 1:
                time.sleep(0.5)
    return {"ok": False, "body": {}, "mode": "live", "error": last_error}


def _live_execute(canonical_id: str, args: dict, headers: dict) -> dict:
    """Runtime SDK if installed, else the `swy` CLI kernel.

    CLI form (verified against `swy exec --help`, swytchcode v2.23.7):
      stdin : {"tool": "<canonical_id>", "args": {...}}  |  swy exec [flags]
      flags : --json (normalized output) · --header k=v (repeatable)
    The kernel is offline-capable (reads tooling.json + fetched bundles only);
    credentials come from `swy auth connect <provider>`, not from this code."""
    if _sdk_available():  # pragma: no cover - depends on local install
        try:
            from swytchcode_runtime import Runtime  # type: ignore

            rt = Runtime()  # type: ignore[call-arg]
            result = rt.tools.execute(canonical_id, {"args": args, "headers": headers})
            return result if isinstance(result, dict) else {"result": result}
        except ImportError:
            pass

    cmd = ["swy", "exec", "--json"]
    for k, v in headers.items():
        cmd += ["--header", f"{k}={v}"]
    proc = subprocess.run(  # noqa: S603
        cmd,
        input=json.dumps({"tool": canonical_id, "args": args}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or "swy exec failed"
        if "not found in any fetched providers" in err:
            err += " — run ./scripts/setup.sh (swy get <provider>) first"
        if "Failed to fetch provider bundles" in err:
            err += " — registry unreachable; fetch bundles once with ./scripts/setup.sh"
        raise RuntimeError(err)
    out = json.loads(proc.stdout)
    if isinstance(out, dict) and out.get("_simulated"):  # --demo fallback path
        out["mode_note"] = "simulated by swy --demo"
    return out


def live(toolkit: str) -> bool:
    """Is this toolkit callable live right now? Used by intake (seed fallback)."""
    if mode() == "mock":
        return False
    if _env("GMAIL_ENABLED") != "1" and toolkit == "gmail":
        return False
    return _sdk_available() or _cli_present()


def _cli_present() -> bool:
    from shutil import which

    return which("swy") is not None


def reset_idempotency() -> None:
    _idempotency_store.clear()
