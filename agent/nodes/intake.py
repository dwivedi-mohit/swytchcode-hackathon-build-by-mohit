"""intake node — Gmail search via Swytchcode, honest seed fallback (E3)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .. import swx
from ..llm import llm_json
from ..state import Invoice, InvoiceState, new_trace_event
from .base import add_error, emit_log, env_int, record

SEED_PATH = Path(__file__).resolve().parents[2] / "seed" / "invoices.json"
GMAIL_QUERY = os.getenv("GMAIL_QUERY", "from:(billing OR invoice) is:unread")

PARSE_SYSTEM = """Extract invoices from this email content. Respond with JSON array only:
[{"id": "...", "vendor": "...", "amount": number|null, "currency": "INR",
  "due_date": "YYYY-MM-DD", "status_hint": "..."}]"""


def _load_seed() -> list[Invoice]:
    data = json.loads(SEED_PATH.read_text())
    out = []
    for inv in data["invoices"]:
        out.append(
            Invoice(
                id=str(inv["id"]),
                vendor=inv["vendor"],
                amount=inv.get("amount"),
                currency=inv.get("currency", "INR"),
                due_date=inv.get("due_date", ""),
                status_hint=inv.get("status_hint", ""),
                email_ref=inv.get("email_ref", "seed"),
                raw_excerpt=inv.get("status_hint", ""),
            )
        )
    return out


def _dedupe(invoices: list[Invoice]) -> list[Invoice]:
    seen, out = set(), []  # X3
    for inv in invoices:
        if inv["id"] in seen:
            continue
        seen.add(inv["id"])
        out.append(inv)
    return out


def _fetch_gmail() -> tuple[list[Invoice], list[str]]:
    """Live Gmail intake. Returns (invoices, errors)."""
    invoices: list[Invoice] = []
    errors: list[str] = []
    listing = swx.execute(
        "gmail.messages.list",
        {"q": GMAIL_QUERY, "maxResults": env_int("MAX_INVOICES", 10)},
        write=False,
    )
    if not listing["ok"]:
        return [], [f"Gmail search failed: {listing['error']}"]
    messages = listing["body"].get("messages", [])
    for msg in messages[: env_int("MAX_INVOICES", 10)]:
        got = swx.execute("gmail.messages.get", {"id": msg.get("id"), "format": "full"})
        if not got["ok"]:
            errors.append(f"message {msg.get('id')} unreadable: {got['error']}")
            continue
        body = got["body"]
        content = f"Subject: {body.get('subject','')}\n{body.get('snippet','')}"
        parsed, _src = llm_json(PARSE_SYSTEM, content, lambda: [])  # E11: empty on parse fail
        if not parsed:
            errors.append(f"could not parse invoice in message {msg.get('id')} — skipped")
            continue
        for p in parsed:
            if not isinstance(p, dict) or not p.get("id"):
                continue
            invoices.append(
                Invoice(
                    id=str(p["id"]),
                    vendor=str(p.get("vendor", "unknown")),
                    amount=p.get("amount") if isinstance(p.get("amount"), (int, float)) else None,
                    currency=str(p.get("currency", "INR")),
                    due_date=str(p.get("due_date", "")),
                    status_hint=str(p.get("status_hint", "")),
                    email_ref=f"gmail:{msg.get('id')}",
                    raw_excerpt=content[:200],
                )
            )
    return invoices, errors


def intake_node(state: InvoiceState) -> dict:
    if swx.live("gmail"):
        invoices, errors = _fetch_gmail()
        source, status = "gmail", "ok"
        for e in errors:
            add_error(state, e)
        if not invoices and not errors:
            # E4 — clean empty result, suggest broader query
            add_error(state, f"No unpaid invoices found in query `{GMAIL_QUERY}`")
    else:
        invoices = _load_seed()  # E3 — honest demo data
        source, status = "gmail", "seed"

    invoices = _dedupe(invoices)
    cap = env_int("MAX_INVOICES", 10)
    truncated = len(invoices) > cap  # X8
    invoices = invoices[:cap]

    if truncated:
        add_error(state, f"Input capped at {env_int('MAX_INVOICES', 10)} invoices (safety limit)")

    ev = new_trace_event(
        node="intake",
        reasoning=(
            f"Found {len(invoices)} invoice(s) via {source}"
            + (" — DEMO DATA (gmail not connected)" if status == "seed" else "")
        ),
        toolkit="gmail",
        canonical_id="gmail.messages.list",
        request={"q": GMAIL_QUERY, "maxResults": cap},
        response={"count": len(invoices), "ids": [i["id"] for i in invoices]},
        decision=f"parse {len(invoices)} invoices → classify",
        status=status,
    )
    record(state, ev)
    if status == "seed":
        emit_log(state, "Gmail unavailable → seed/invoices.json (E3)", "warning")
    return {"invoices": invoices, "trace": state["trace"], "errors": state["errors"]}
