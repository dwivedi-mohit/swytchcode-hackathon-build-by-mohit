"""slack_summary node — post a summary built from actual results, not the plan."""
from __future__ import annotations

import os

from .. import swx
from ..state import InvoiceState, new_trace_event
from .base import add_error, record


def build_summary(state: InvoiceState) -> str:
    results = state.get("results", {})
    decisions = state.get("decisions", [])
    invoices = {i["id"]: i for i in state.get("invoices", [])}
    run_id = state.get("run_id", "run")[:6]

    chased, escalated, logged, notes = [], [], 0, []
    for d in decisions:
        inv = invoices[d["invoice_id"]]
        r = results.get(d["invoice_id"], {})
        label = d["label"]
        if r.get("paypal_id"):
            chased.append(f"Chased {inv['vendor']} ₹{inv['amount']} → {r['paypal_id']}")
        elif r.get("paypal_status") == "SKIPPED":
            chased.append(f"Chase of {inv['vendor']} #{inv['id']} skipped (not approved)")
        elif r.get("paypal_status") == "FAILED":
            chased.append(f"Chase of {inv['vendor']} #{inv['id']} FAILED (PayPal error)")
        if r.get("jira_key"):
            escalated.append(f"Escalated dispute {inv['vendor']} #{inv['id']} → {r['jira_key']}")
        if label in ("DUE_SOON", "PAID") and not r.get("paypal_id") and not r.get("jira_key"):
            logged += 1
            notes.append(f"{'Due soon' if label == 'DUE_SOON' else 'Paid'}: {inv['vendor']} #{inv['id']}")

    lines = [f"📋 Billing run {run_id} · {len(decisions)} invoices"]
    lines += [f"• {c}" for c in chased]
    lines += [f"• {e}" for e in escalated]
    notion = results.get("notion", {})
    if notion.get("rows"):
        lines.append(f"• Logged {notion['rows']} rows in Notion Ops Log")
    lines += [f"• {n}" for n in notes]
    for err in state.get("errors", []):
        lines.append(f"⚠️ {err}")
    return "\n".join(lines)


def slack_summary_node(state: InvoiceState) -> dict:
    run_id = state.get("run_id", "")
    results = dict(state.get("results", {}))
    text = build_summary(state)
    channel = os.getenv("SLACK_CHANNEL", "#finance-ops")

    call = swx.execute(
        "slack.chat.postmessage.create",
        {"body": {"channel": channel, "text": text}},
        run_id=run_id, invoice_id="summary", write=True,
    )
    if call["ok"]:
        ev = new_trace_event(
            node="slack_summary",
            reasoning=f"Summary composed from real PayPal/Jira/Notion responses and posted to {channel}.",
            toolkit="slack", canonical_id="slack.chat.postmessage.create",
            request={"channel": channel, "text": text},
            response=call["body"],
            decision="final answer quotes the posted summary",
            status="ok",
        )
        record(state, ev)
        results["slack"] = {"ts": call["body"].get("ts", ""), "text": text,
                            "channel": call["body"].get("channel", channel)}
    else:  # E8 / X9 — summary falls back to inline text
        ev = new_trace_event(
            node="slack_summary",
            reasoning=f"Slack post failed: {call['error']} — summary will render inline instead (X9).",
            toolkit="slack", canonical_id="slack.chat.postmessage.create",
            request={"channel": channel}, response={"error": call["error"]},
            decision="inline fallback", status="failed",
        )
        record(state, ev)
        add_error(state, f"Slack post failed: {call['error']} — summary shown inline")
        results["slack"] = {"ts": None, "text": text, "channel": None}

    return {"results": results, "trace": state["trace"], "errors": state["errors"]}
