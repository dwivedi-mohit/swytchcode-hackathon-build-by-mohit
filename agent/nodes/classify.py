"""classify node — label every invoice and choose one action per invoice (LLM)."""
from __future__ import annotations

from datetime import date

from ..llm import llm_json
from ..state import Decision, Invoice, InvoiceState, Label, new_trace_event
from .base import as_dicts, record

SYSTEM = """You classify invoices for LedgerPilot.
Labels: OVERDUE (past due, unpaid), DISPUTED (customer contests the charge),
DUE_SOON (not yet due), PAID (settled).
Actions: paypal_chase (overdue only), jira_escalate (disputed only),
log_only (due soon / paid).
A dispute ALWAYS wins over overdue. Respond with JSON array only:
[{"invoice_id": "...", "label": "...", "action": "...", "reason": "one line"}]"""

LABELS = {"OVERDUE", "DISPUTED", "DUE_SOON", "PAID"}
ACTIONS = {"paypal_chase", "jira_escalate", "log_only", "skip"}


def _rule_decision(inv: Invoice) -> Decision:
    hint = (inv.get("status_hint") or "").lower()
    excerpt = (inv.get("raw_excerpt") or "").lower()
    text = hint + " " + excerpt
    due = inv.get("due_date") or ""
    today = date.today().isoformat()

    if "dispute" in text or "wrong amount" in text:  # X2 — dispute dominates
        label: Label = "DISPUTED"
        action = "jira_escalate"
        reason = "customer contests the charge → escalate, do not chase payment"
    elif "paid" in text:
        label, action = "PAID", "log_only"
        reason = "already settled — record only"
    elif "overdue" in text or (due and due < today):
        if inv.get("amount") is None:  # X4 — unknown amount, don't move value
            label, action = "DUE_SOON", "log_only"
            reason = "past due but amount unknown — log for manual review"
        else:
            label, action = "OVERDUE", "paypal_chase"
            reason = f"past due (due {due}) → chase payment via PayPal"
    else:
        label, action = "DUE_SOON", "log_only"
        reason = "not yet due — monitor"
    return {"invoice_id": inv["id"], "label": label, "action": action, "reason": reason}


def _validate(raw: list, invoices: list[Invoice]) -> list[Decision]:
    by_id = {i["id"]: i for i in invoices}
    out: list[Decision] = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        inv_id = str(item.get("invoice_id", ""))
        if inv_id not in by_id or inv_id in seen:
            continue
        label = str(item.get("label", "")).upper()
        action = str(item.get("action", ""))
        if label not in LABELS or action not in ACTIONS:
            d = _rule_decision(by_id[inv_id])  # malformed LLM output → rules
        else:
            d = {"invoice_id": inv_id, "label": label, "action": action,  # type: ignore[typeddict-item]
                 "reason": str(item.get("reason", ""))}
        seen.add(inv_id)
        out.append(d)
    # any invoice the LLM missed → rules
    for inv in invoices:
        if inv["id"] not in seen:
            out.append(_rule_decision(inv))
    return out


def classify_node(state: InvoiceState) -> dict:
    invoices: list[Invoice] = state.get("invoices", [])
    if not invoices:
        ev = new_trace_event(
            node="classify", reasoning="No invoices to classify.", toolkit="none",
            decision="nothing to do", status="skipped",
        )
        record(state, ev)
        return {"decisions": [], "trace": state["trace"]}

    def fallback() -> list:
        return [_rule_decision(i) for i in invoices]

    prompt_blob = "\n".join(
        f"- id={i['id']} vendor={i['vendor']} amount={i['amount']} due={i['due_date']} "
        f"hint={i['status_hint']!r}"
        for i in invoices
    )
    raw, source = llm_json(SYSTEM, prompt_blob, fallback)
    decisions = _validate(as_dicts(raw), invoices)

    if state.get("mode") == "read_only":  # read-only: keep labels, force no writes
        for d in decisions:
            if d["action"] in ("paypal_chase", "jira_escalate"):
                d["action"] = "log_only"
                d["reason"] = f"[read-only] {d['label']} observed — no external action taken"

    counts: dict[str, int] = {}
    for d in decisions:
        counts[d["label"]] = counts.get(d["label"], 0) + 1
    ev = new_trace_event(
        node="classify",
        reasoning=f"Labeled {len(decisions)} invoice(s) (llm={source}): " + ", ".join(
            f"{v}×{k}" for k, v in counts.items()
        ),
        toolkit="none",
        decision="; ".join(f"{d['invoice_id']}→{d['label']}/{d['action']}" for d in decisions),
        status="ok",
    )
    record(state, ev)
    return {"decisions": decisions, "trace": state["trace"]}
