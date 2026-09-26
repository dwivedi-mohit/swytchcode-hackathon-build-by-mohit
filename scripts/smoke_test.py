#!/usr/bin/env python3
"""Toolkit smoke test — one benign exec per Swytchcode toolkit, PASS/FAIL matrix (T02).

Floor: exits 1 if fewer than 3 toolkits pass (rubric requirement: >=3).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import swx  # noqa: E402

CHECKS = [
    ("gmail",   "gmail.user.messages.get",      {"userId": "me", "q": "is:unread", "maxResults": 1}, False),
    ("paypal",  "invoices.invoicing.invoices.list",     {},                                   False),
    ("jira",    "jira.api.search.create1",       {"body": {"jql": "order by created DESC", "maxResults": 1}}, False),
    ("notion",  "notion.query.create",   {"data_source_id": "ledgerpilot-ops-log"}, False),
    ("slack",   "slack.chat.postmessage.create",   {"body": {"channel": "#finance-ops", "text": "LedgerPilot smoke test ✅"}}, True),
]
FLOOR = 3


def main() -> int:
    print(f"swx mode: {swx.mode()}\n")
    rows, passed = [], 0
    for toolkit, cid, params, write in CHECKS:
        t0 = time.time()
        res = swx.execute(cid, params, run_id="smoke", invoice_id=toolkit, write=write)
        ms = int((time.time() - t0) * 1000)
        ok = res["ok"]
        passed += ok
        err = res.get("error", "")
        import re
        m = re.search(r'"error":"([^"]{1,160})', err)  # extract JSON error field from CLI stderr
        if m:
            try:
                err = m.group(1).encode().decode("unicode_escape")
            except UnicodeDecodeError:  # raw path separators etc. — keep verbatim
                err = m.group(1)
        rows.append((toolkit, cid, "PASS" if ok else "FAIL", ms, err[:100]))

    w = max(len(r[0]) for r in rows) + 2
    print(f"{'toolkit':<{w}} {'canonical id':<34} {'result':<6} {'ms':>5}  error")
    print("-" * (w + 60))
    for tk, cid, res, ms, err in rows:
        mark = "\033[32m" if res == "PASS" else "\033[31m"
        print(f"{mark}{tk:<{w}}\033[0m {cid:<34} {res:<6} {ms:>5}  {err}")

    print(f"\n{passed}/{len(rows)} toolkits passing (floor: {FLOOR})")
    if swx.mode() == "mock":
        print("⚠ MOCK mode — these PASSes prove wiring, not live auth. "
              "Install/authenticate `swy` and re-run for venue proof (BUILD.md Gate B).")
        return 0
    if passed < FLOOR:
        print("Below floor — fix auth/network, or rely on mock mode for the demo (BUILD.md Gate B).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
