"""paypal_chase node — value-moving call behind the human approval gate."""
from __future__ import annotations

import os

from .. import approvals, swx
from ..state import InvoiceState, new_trace_event
from .base import add_error, env_int, record


def _payload(invoice: dict, decision: dict) -> dict:
    return {
        "invoice": {
            "number": f"INV-{invoice['id']}",
            "recipient": invoice["vendor"],
            "amount": {"value": f"{invoice['amount']:.2f}", "currency": invoice.get("currency", "INR")},
            "note": f"Payment reminder — {decision['reason']}",
        },
        "env": "sandbox",
    }


def paypal_chase_node(state: InvoiceState) -> dict:
    run_id = state.get("run_id", "")
    results = dict(state.get("results", {}))
    by_id = {i["id"]: i for i in state.get("invoices", [])}
    targets = [d for d in state.get("decisions", []) if d["action"] == "paypal_chase"]
    timeout_s = float(env_int("APPROVAL_TIMEOUT_S", 120))

    for d in targets:
        inv = by_id[d["invoice_id"]]
        payload = _payload(inv, d)

        # --- approval gate (SECURITY §2.1) ---
        pa = approvals.create(run_id, inv["id"], payload)
        gate = new_trace_event(
            node="paypal_chase",
            reasoning=f"Invoice #{inv['id']} ({inv['vendor']}, {inv['amount']} {inv.get('currency','INR')}) "
                      "is overdue — PayPal chase requires human approval (policies.json).",
            toolkit="paypal",
            canonical_id="paypal.invoices.send",
            request=payload,
            decision="waiting for operator approval",
            status="pending_approval",
            etype="approval",
            invoice_id=inv["id"],
            request_hash=pa.hash,
        )
        record(state, gate)
        state["approval_pending"] = gate

        approved, how = approvals.wait(pa, timeout_s)
        state["approval_pending"] = None

        if not approved:
            reason = {
                "denied": "Chase cancelled by operator (E6).",
                "timeout": f"Approval timed out after {int(timeout_s)}s — call not executed (E7).",
            }.get(how, f"Approval not granted ({how}).")
            resolve_ev = new_trace_event(
                node="paypal_chase", reasoning=reason, toolkit="paypal",
                decision=f"invoice {inv['id']} → SKIPPED (no PayPal call)",
                status="denied" if how == "denied" else "skipped",
                etype="approval", invoice_id=inv["id"], request_hash=pa.hash,
            )
            record(state, resolve_ev)
            results[inv["id"]] = {"paypal_id": None, "paypal_status": "SKIPPED", "skip_reason": how}
            if how == "denied":
                add_error(state, f"PayPal chase for #{inv['id']} denied by operator")
            else:
                add_error(state, f"PayPal chase for #{inv['id']} timed out")
            continue

        ok_ev = new_trace_event(
            node="paypal_chase", reasoning="Approved by operator — executing PayPal call.",
            toolkit="paypal", decision="approved", status="approved",
            etype="approval", invoice_id=inv["id"], request_hash=pa.hash,
        )
        record(state, ok_ev)

        # --- the actual Swytchcode call ---
        call = swx.execute(
            "paypal.invoices.send", payload, run_id=run_id, invoice_id=inv["id"], write=True
        )
        if call["ok"]:
            pid = call["body"].get("id", "")
            ev = new_trace_event(
                node="paypal_chase",
                reasoning=f"PayPal accepted the chase for #{inv['id']} → {pid} ({call['mode']}).",
                toolkit="paypal", canonical_id="paypal.invoices.send",
                request=payload, response=call["body"],
                decision=f"results[{inv['id']}].paypal_id={pid}; Status=CHASED in Notion",
                status="ok",
            )
            record(state, ev)
            results[inv["id"]] = {"paypal_id": pid, "paypal_status": "CHASED"}
        else:  # E5 — branch continues without PayPal
            ev = new_trace_event(
                node="paypal_chase",
                reasoning=f"PayPal chase failed: {call['error']} — continuing without it.",
                toolkit="paypal", canonical_id="paypal.invoices.send",
                request=payload, response={"error": call["error"]},
                decision=f"results[{inv['id']}].paypal_status=FAILED; Slack will note the failure",
                status="failed",
            )
            record(state, ev)
            add_error(state, f"PayPal chase for #{inv['id']} failed: {call['error']}")
            results[inv["id"]] = {"paypal_id": None, "paypal_status": "FAILED"}

    if not targets:
        ev = new_trace_event(
            node="paypal_chase", reasoning="No overdue invoices to chase.", toolkit="paypal",
            decision="no-op", status="skipped",
        )
        record(state, ev)

    return {"results": results, "trace": state["trace"], "errors": state["errors"],
            "approval_pending": None}
