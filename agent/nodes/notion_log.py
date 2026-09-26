"""notion_log node — one Ops DB row per invoice, Status from real API responses."""
from __future__ import annotations

import os
import time

from .. import swx
from ..state import InvoiceState, new_trace_event
from .base import add_error, record


def _status_for(inv_id: str, label: str, results: dict) -> tuple[str, dict]:
    r = results.get(inv_id, {})
    paypal_id = r.get("paypal_id")
    jira_key = r.get("jira_key")
    if r.get("paypal_status") in ("SKIPPED", "FAILED"):
        return "SKIPPED", r
    if paypal_id:
        return "CHASED", r
    if jira_key:
        return "DISPUTED", r
    if label == "PAID":
        return "PAID", r
    if label == "OVERDUE":
        # read-only run or failed chase already handled above
        return "LOGGED", r
    return "LOGGED", r


def notion_log_node(state: InvoiceState) -> dict:
    run_id = state.get("run_id", "")
    results = dict(state.get("results", {}))
    decisions = state.get("decisions", [])
    invoices = {i["id"]: i for i in state.get("invoices", [])}
    if not decisions:
        return {"results": results, "trace": state["trace"], "errors": state["errors"]}

    # E10 dedupe — skip if this run already logged
    query = swx.execute(
        "notion.query.create",
        {"data_source_id": os.getenv("NOTION_DATA_SOURCE_ID", "ledgerpilot-ops-log"),
         "body": {"filter": {"property": "Run ID", "rich_text": {"equals": run_id}}}},
        run_id=run_id, write=False,
    )
    if query["ok"] and query["body"].get("results"):
        ev = new_trace_event(
            node="notion_log",
            reasoning=f"Run {run_id} already has {len(query['body']['results'])} rows — deduped (E10).",
            toolkit="notion", canonical_id="notion.query.create",
            request={"run_id": run_id}, response={"count": len(query["body"]["results"])},
            decision="skip row creation", status="skipped",
        )
        record(state, ev)
        return {"results": results, "trace": state["trace"], "errors": state["errors"]}

    created, pages, errors = 0, {}, []
    for d in decisions:
        inv = invoices[d["invoice_id"]]
        status, r = _status_for(inv["id"], d["label"], results)
        row = {
            "parent": {"database_id": os.getenv("NOTION_DATA_SOURCE_ID", "ledgerpilot-ops-log")},
            "properties": {
                "Invoice ID": inv["id"],
                "Vendor": inv["vendor"],
                "Amount": inv.get("amount"),
                "Due Date": inv.get("due_date", ""),
                "Label": d["label"],
                "Status": status,  # from actual responses, never the plan (§4.2 rule)
                "PayPal Invoice ID": r.get("paypal_id") or "",
                "Jira Key": r.get("jira_key") or "",
                "Run ID": run_id,
                "Ran At": time.strftime("%Y-%m-%d", time.gmtime()),
            },
        }
        call = swx.execute("notion.page.create", {"body": row}, run_id=run_id,
                           invoice_id=inv["id"], write=True)
        if call["ok"]:
            created += 1
            pages[inv["id"]] = call["body"].get("page_id") or call["body"].get("id", "")
        else:  # E8
            errors.append(f"Notion row for #{inv['id']} failed: {call['error']}")

    results["notion"] = {"rows": created, "pages": pages}
    ev = new_trace_event(
        node="notion_log",
        reasoning=f"Wrote {created}/{len(decisions)} Ops DB row(s) with status from live responses "
                  f"({', '.join(sorted(set(_status_for(d['invoice_id'], d['label'], results)[0] for d in decisions)))}).",
        toolkit="notion", canonical_id="notion.page.create",
        request={"rows": len(decisions)},
        response={"created": created, "pages": pages},
        decision=f"results.notion.rows={created} → Slack summary",
        status="ok" if created == len(decisions) else ("failed" if created == 0 else "ok"),
    )
    record(state, ev)
    for e in errors:
        add_error(state, e)
    return {"results": results, "trace": state["trace"], "errors": state["errors"]}
