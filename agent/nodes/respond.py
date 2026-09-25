"""respond node — assemble the operator-facing final answer."""
from __future__ import annotations

from ..llm import warnings as llm_warnings
from ..state import InvoiceState, new_trace_event
from .base import record

EMPTY_HINT = "Try broadening the query — e.g. `from:(billing OR invoice)`."


def _coins(state: InvoiceState) -> str:
    results = state.get("results", {})
    decisions = state.get("decisions", [])
    invoices = {i["id"]: i for i in state.get("invoices", [])}
    lines: list[str] = []

    for d in decisions:
        inv = invoices[d["invoice_id"]]
        r = results.get(d["invoice_id"], {})
        name = f"{inv['vendor']} #{inv['id']}"
        if r.get("paypal_id"):
            lines.append(f"• Chased {name} (₹{inv.get('amount')}) — PayPal `{r['paypal_id']}`")
        elif r.get("paypal_status") in ("SKIPPED", "FAILED"):
            why = "not approved" if r["paypal_status"] == "SKIPPED" else "PayPal error"
            lines.append(f"• {name} — chase skipped ({why})")
        if r.get("jira_key"):
            lines.append(f"• Escalated {name} → Jira `{r['jira_key']}`")
        if d["label"] == "PAID":
            lines.append(f"• {name} — already paid, logged")
        elif d["label"] == "DUE_SOON":
            lines.append(f"• {name} — due soon, no action needed")

    notion = results.get("notion", {})
    if notion.get("rows"):
        lines.append(f"• Notion Ops Log: {notion['rows']} row(s) written")
    slack = results.get("slack", {})
    if slack.get("ts"):
        lines.append(f"• Slack `#finance-ops`: posted (ts `{slack['ts']}`)")
    return "\n".join(lines)


def respond_node(state: InvoiceState) -> dict:
    decisions = state.get("decisions", [])
    mode = state.get("mode", "write")

    if not state.get("invoices"):
        answer = f"No unpaid invoices found in the intake query.\n\n{EMPTY_HINT}"
    elif mode == "read_only":
        lines = ["**Read-only run** — no external calls were made.\n"]
        for d in decisions:
            inv = next(i for i in state["invoices"] if i["id"] == d["invoice_id"])
            lines.append(f"• {inv['vendor']} #{d['invoice_id']}: {d['label']} — {d['reason']}")
        answer = "\n".join(lines)
    else:
        answer = _coins(state) or "Nothing to act on."

    errors = list(state.get("errors", []))
    warn = [w for w in llm_warnings if w not in errors]
    if warn:
        answer += "\n\n_Notes:_\n" + "\n".join(f"• {w}" for w in warn)
    if errors:
        answer += "\n\n_Issues:_\n" + "\n".join(f"• {e}" for e in errors)

    ev = new_trace_event(
        node="respond",
        reasoning=f"Final answer assembled from {len(state.get('trace', []))} trace events, "
                  f"{len(errors)} issue(s).",
        toolkit="none", decision="run complete", status="ok",
    )
    record(state, ev)
    return {"final_answer": answer, "trace": state["trace"]}
