#!/usr/bin/env python3
"""Gate E — live end-to-end driver: POST /run → auto-approve PayPal → real-ID summary.

Proves a full live run without a browser: real LLM plan, real Swytchcode calls
(PayPal invoice create+send behind the approval gate, Notion log, Jira issue,
Slack summary), streaming SSE trace.

Usage:
    python -m server.main &            # live server (MOCK_* unset, GMAIL_ENABLED=0 for seed intake)
    python scripts/live_e2e.py         # run once, prints trace + harvested real IDs
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_PROMPT = (
    "Run billing day: chase overdue invoices, escalate disputed ones to Jira, "
    "log everything to Notion and post a Slack summary."
)

ID_KEYS = {"id", "invoice_id", "ts", "page_id", "key", "issue_id", "database_id"}


def post(base: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def stream(base: str, run_id: str, timeout_s: float):
    """Read SSE line-by-line (read(n) would buffer ~4KB and stall past the
    120s approval window before delivering the approval event)."""
    req = urllib.request.Request(base + f"/stream/{run_id}")
    with urllib.request.urlopen(req, timeout=60) as r:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            raw = r.readline()
            if not raw:
                return
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if line.startswith("data: "):
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue


def harvest(obj, out: set) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ID_KEYS and isinstance(v, str) and v:
                out.add(f"{k}={v}")
            harvest(v, out)
    elif isinstance(obj, list):
        for v in obj:
            harvest(v, out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8001")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--deny", action="store_true", help="deny the PayPal approval instead")
    ap.add_argument("--timeout", type=float, default=600)
    args = ap.parse_args()

    try:
        rid = post(args.base, "/run", {"prompt": args.prompt})["run_id"]
    except urllib.error.HTTPError as e:
        print(f"server error {e.code}: {e.read().decode()[:300]}")
        return 1
    print(f"run_id={rid}  base={args.base}\n")

    real: set[str] = set()
    final, failed = "", False
    for ev in stream(args.base, rid, args.timeout):
        t = ev.get("type")
        if t == "approval":
            print(f"  ⏸ APPROVAL invoice_id={ev.get('invoice_id')} hash={ev.get('request_hash')}")
            if ev.get("status") == "pending_approval":
                payload = {"run_id": rid, "invoice_id": ev.get("invoice_id", ""),
                           "approved": not args.deny, "request_hash": ev.get("request_hash", "")}
                try:
                    post(args.base, "/approve", payload)
                    print("  → approved ✓" if not args.deny else "  → denied")
                except urllib.error.HTTPError as e:
                    print(f"  → approve FAILED {e.code}: {e.read().decode()[:200]}")
            else:
                print(f"  → (approval event status={ev.get('status')})")
        elif t == "trace":
            print(f"  [{ev.get('status')}] {ev.get('node'):<14} {ev.get('canonical_id', ''):<34} {ev.get('decision', '')}")
            harvest(ev.get("response", {}), real)
        elif t == "log":
            print(f"  log: {ev.get('text', '')}")
        elif t == "done":
            final = ev.get("final_answer", "")
            for err in ev.get("errors", []):
                print(f"  ! error: {err}")
        elif t == "error":
            print(f"  !! {ev.get('text', '')}")
            failed = True

    print("\n=== harvested real IDs ===")
    for s in sorted(real):
        print(f"  {s}")
    print("\n=== final answer ===\n" + (final or "(none)"))
    if failed or not final:
        print("\nGATE E: FAIL")
        return 1
    print("\nGATE E: PASS (live LLM + live toolkits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
