"""LangGraph assembly — nodes, conditional routing, checkpointer (build contract §6).

Routing (conditional edges = agency proof):
  plan → intake → classify
  classify → (read_only | no writes) → respond
           → paypal needed        → paypal_chase → jira? → notion_log
           → jira needed          → jira_escalate → notion_log
           → logs only            → notion_log
  notion_log → slack_summary → respond
PayPal is never reachable for DISPUTED invoices (routing only looks at actions
produced by classify, where dispute ⇒ jira_escalate).
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes import classify, intake, jira_escalate, notion_log, paypal_chase, plan, respond, slack_summary
from .state import InvoiceState, initial_state


def _route_after_classify(state: InvoiceState) -> str:
    if state.get("mode") == "read_only":
        return "respond"
    actions = {d["action"] for d in state.get("decisions", [])}
    if "paypal_chase" in actions:
        return "paypal_chase"
    if "jira_escalate" in actions:
        return "jira_escalate"
    if state.get("decisions"):
        return "notion_log"
    return "respond"


def _route_after_paypal(state: InvoiceState) -> str:
    if any(d["action"] == "jira_escalate" for d in state.get("decisions", [])):
        return "jira_escalate"
    return "notion_log"


def build_graph():
    g = StateGraph(InvoiceState)
    g.add_node("plan", plan.plan_node)
    g.add_node("intake", intake.intake_node)
    g.add_node("classify", classify.classify_node)
    g.add_node("paypal_chase", paypal_chase.paypal_chase_node)
    g.add_node("jira_escalate", jira_escalate.jira_escalate_node)
    g.add_node("notion_log", notion_log.notion_log_node)
    g.add_node("slack_summary", slack_summary.slack_summary_node)
    g.add_node("respond", respond.respond_node)

    g.set_entry_point("plan")
    g.add_edge("plan", "intake")
    g.add_edge("intake", "classify")
    g.add_conditional_edges(
        "classify",
        _route_after_classify,
        ["paypal_chase", "jira_escalate", "notion_log", "respond"],
    )
    g.add_conditional_edges("paypal_chase", _route_after_paypal, ["jira_escalate", "notion_log"])
    g.add_edge("jira_escalate", "notion_log")
    g.add_edge("notion_log", "slack_summary")
    g.add_edge("slack_summary", "respond")
    g.add_edge("respond", END)

    return g.compile(checkpointer=MemorySaver())


def run(prompt: str, run_id: str) -> InvoiceState:
    graph = build_graph()
    final: InvoiceState = graph.invoke(  # type: ignore[arg-type]
        initial_state(prompt, run_id),
        {"configurable": {"thread_id": run_id}},
    )
    return final  # type: ignore[return-value]
