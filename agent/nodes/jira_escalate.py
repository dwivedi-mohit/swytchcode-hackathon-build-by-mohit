"""jira_escalate node — disputed invoices become tracked issues (PayPal skipped)."""
from __future__ import annotations

from .. import swx
from ..state import InvoiceState, new_trace_event
from .base import add_error, record


def jira_escalate_node(state: InvoiceState) -> dict:
    run_id = state.get("run_id", "")
    results = dict(state.get("results", {}))
    by_id = {i["id"]: i for i in state.get("invoices", [])}
    targets = [d for d in state.get("decisions", []) if d["action"] == "jira_escalate"]

    for d in targets:
        inv = by_id[d["invoice_id"]]
        priority = "High" if (inv.get("amount") or 0) > 50000 else "Medium"
        fields = {
            "fields": {
                "project": {"key": "OPS"},
                "summary": f"Dispute: {inv['vendor']} #{inv['id']}",
                "issuetype": {"name": "Bug"},
                "priority": {"name": priority},
                "description": (
                    f"Invoice {inv['id']} ({inv['vendor']}, {inv.get('currency','INR')} {inv.get('amount')}) "
                    f"disputed by customer.\nReason: {d['reason']}\nDue: {inv.get('due_date','')}\n"
                    f"Excerpt: {inv.get('raw_excerpt','')}"
                ),
            }
        }
        call = swx.execute(
            "jira.issues.create", fields, run_id=run_id, invoice_id=inv["id"], write=True
        )
        if call["ok"]:
            key = call["body"].get("key", "")
            ev = new_trace_event(
                node="jira_escalate",
                reasoning=f"Dispute on #{inv['id']} → Jira {key} (priority {priority}). "
                          "PayPal chase deliberately skipped for this invoice.",
                toolkit="jira", canonical_id="jira.issues.create",
                request=fields, response=call["body"],
                decision=f"results[{inv['id']}].jira_key={key}; Status=DISPUTED in Notion",
                status="ok",
            )
            record(state, ev)
            results[inv["id"]] = {**results.get(inv["id"], {}), "jira_key": key,
                                  "jira_status": "DISPUTED"}
        else:  # E8
            ev = new_trace_event(
                node="jira_escalate",
                reasoning=f"Jira escalation failed: {call['error']}", toolkit="jira",
                canonical_id="jira.issues.create", request=fields,
                response={"error": call["error"]},
                decision="continue without issue key", status="failed",
            )
            record(state, ev)
            add_error(state, f"Jira escalation for #{inv['id']} failed: {call['error']}")
            results[inv["id"]] = {**results.get(inv["id"], {}), "jira_key": None,
                                  "jira_status": "FAILED"}

    if not targets:
        ev = new_trace_event(
            node="jira_escalate", reasoning="No disputed invoices.", toolkit="jira",
            decision="no-op", status="skipped",
        )
        record(state, ev)

    return {"results": results, "trace": state["trace"], "errors": state["errors"]}
