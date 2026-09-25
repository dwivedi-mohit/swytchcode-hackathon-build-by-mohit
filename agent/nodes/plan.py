"""plan node — interpret the operator's prompt into mode + ordered plan."""
from __future__ import annotations

from ..llm import llm_json
from ..state import InvoiceState, new_trace_event
from .base import record

SYSTEM = """You are the planner for LedgerPilot, an AI revenue-ops agent.
Given the operator's prompt, decide:
- mode: "write" if the prompt asks the agent to DO something in external tools
  (chase/send/log/post/escalate/create/update), else "read_only".
- plan: 4-7 short ordered steps the agent will take.
Respond with JSON only: {"mode": "write"|"read_only", "plan": ["step", ...]}"""

WRITE_MARKERS = (
    "chase", "send", "post", "escalate", "log", "create", "billing day",
    "overdue", "invoice", "dispute", "update", "pay", "remind",
)
READ_MARKERS = ("what did", "show me", "how many", "summarize what", "list the", "check the status")


def _fallback(prompt: str) -> dict:
    p = prompt.lower()
    looks_read = any(m in p for m in READ_MARKERS)  # question form wins (X1-style)
    wants_write = any(m in p for m in WRITE_MARKERS)
    mode = "read_only" if looks_read else "write"
    if mode == "read_only":
        plan = [
            "read invoice history (no external calls)",
            "answer the operator's question from existing data",
        ]
    else:
        plan = [
            "intake: pull unpaid invoice emails",
            "classify: label each invoice (overdue / disputed / due soon / paid)",
            "chase overdue via PayPal (human approval required)",
            "escalate disputes to Jira",
            "log all outcomes to Notion",
            "post summary to Slack",
        ]
    return {"mode": mode, "plan": plan}


def plan_node(state: InvoiceState) -> dict:
    prompt = state["prompt"]

    def fallback() -> dict:
        return _fallback(prompt)

    data, source = llm_json(SYSTEM, f"Prompt: {prompt}", fallback)
    mode = "read_only" if str(data.get("mode", "")).lower() in ("read_only", "read-only", "readonly") else "write"
    plan = [str(s) for s in data.get("plan", [])] or fallback()["plan"]

    ev = new_trace_event(
        node="plan",
        reasoning=f"Interpreted prompt as mode={mode}; announced {len(plan)} steps (llm={source}).",
        toolkit="none",
        decision=" → ".join(plan[:3]) + ("…" if len(plan) > 3 else ""),
        status="ok",
    )
    record(state, ev)
    return {"mode": mode, "plan": plan, "trace": state["trace"]}
