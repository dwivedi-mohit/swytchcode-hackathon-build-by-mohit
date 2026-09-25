"""MOCK_LLM + MOCK_SWX E2E — full graph runs with zero keys and zero network (T18)."""
from __future__ import annotations

import os

import pytest

os.environ["MOCK_LLM"] = "1"
os.environ["MOCK_SWX"] = "1"
os.environ["GMAIL_ENABLED"] = "0"
os.environ["AUTO_APPROVE"] = "1"
os.environ.pop("APPROVAL_TIMEOUT_S", None)

from agent import approvals, swx  # noqa: E402
from agent.graph import run  # noqa: E402
from agent.nodes import slack_summary  # noqa: E402

BILLING = (
    "It's billing day. Find unpaid invoices, chase overdue ones with PayPal, "
    "escalate disputes to Jira, log everything to Notion, and summarize in Slack."
)


@pytest.fixture(autouse=True)
def _clean():
    swx.reset_idempotency()
    yield
    swx.reset_idempotency()


@pytest.fixture
def result():
    return run(BILLING, run_id="test-run-1")


def test_full_run_trace(result):
    trace = result["trace"]
    assert len(trace) >= 6, f"expected >=6 trace events, got {len(trace)}"
    toolkits = {e["toolkit"] for e in trace}
    assert {"paypal", "jira", "notion", "slack"} <= toolkits
    assert "gmail" in toolkits  # seed intake still reports toolkit gmail
    nodes = [e["node"] for e in trace]
    assert nodes[0] == "plan"
    assert "respond" in nodes


def test_seed_intake_four_invoices(result):
    assert len(result["invoices"]) == 4
    seed_events = [e for e in result["trace"] if e["node"] == "intake"]
    assert seed_events and seed_events[0]["status"] == "seed"  # E3 honesty pill


def test_disputed_invoice_never_reaches_paypal(result):
    paypal_targets = {e["invoice_id"] for e in result["trace"]
                      if e["node"] == "paypal_chase" and e["type"] == "approval"}
    assert "1043" not in paypal_targets  # disputed → Jira only
    assert "1042" in paypal_targets      # overdue → PayPal
    assert result["results"]["1043"].get("jira_key"), "dispute must produce a Jira key"


def test_approval_gate_used(result):
    pending = [e for e in result["trace"]
               if e["node"] == "paypal_chase" and e["status"] == "pending_approval"]
    assert pending and pending[0].get("request_hash"), "approval card must be emitted"
    approved = [e for e in result["trace"]
                if e["node"] == "paypal_chase" and e["status"] == "approved"]
    assert approved


def test_final_answer_contains_live_ids(result):
    answer = result["final_answer"]
    assert "INV-" in answer, "PayPal invoice id missing from final answer"
    assert "OPS-" in answer, "Jira key missing from final answer"
    assert "Notion Ops Log" in answer
    assert not result["errors"], f"unexpected errors: {result['errors']}"


def test_paypal_result_drives_notion_status(result):
    # Status copied from actual responses, never from the plan (arch §4.2)
    assert result["results"]["1042"]["paypal_status"] == "CHASED"
    assert result["results"]["1043"]["jira_key"].startswith("OPS-")


def test_read_only_run_makes_no_write_calls(result):
    import agent.graph as graph_mod

    r = run("What did we chase this week?", run_id="test-run-ro")
    assert r["mode"] == "read_only"
    write_nodes = {e["node"] for e in r["trace"]} & {
        "paypal_chase", "jira_escalate", "notion_log", "slack_summary"
    }
    # read_only routes straight to respond — only no-op markers allowed
    for e in r["trace"]:
        if e["node"] in ("paypal_chase", "jira_escalate", "notion_log", "slack_summary"):
            assert e["status"] == "skipped", f"write node ran in read-only mode: {e}"
    assert "final_answer" in r and r["final_answer"]
    assert "Read-only" in r["final_answer"]


def test_denied_approval_skips_paypal():
    os.environ["AUTO_APPROVE"] = "0"
    os.environ["APPROVAL_TIMEOUT_S"] = "1"
    try:
        swx.reset_idempotency()
        r = run(BILLING, run_id="test-run-timeout")
        res = r["results"].get("1042", {})
        assert res.get("paypal_status") == "SKIPPED"  # E7
        assert r["results"]["1043"].get("jira_key"), "other branches continue after timeout"
        assert any("timed out" in e for e in r["errors"])
        timeout_ev = [e for e in r["trace"] if e["node"] == "paypal_chase"
                      and e["type"] == "approval" and e["status"] == "skipped"]
        assert timeout_ev
    finally:
        os.environ["AUTO_APPROVE"] = "1"
        os.environ.pop("APPROVAL_TIMEOUT_S", None)


def test_re_run_does_not_double_chase():
    r1 = run(BILLING, run_id="run-a")
    r2 = run(BILLING, run_id="run-b")
    assert r1["results"]["1042"]["paypal_id"] == r2["results"]["1042"]["paypal_id"]  # E10/T25
    assert r1["results"]["1043"]["jira_key"] == r2["results"]["1043"]["jira_key"]


def test_approval_hash_mismatch_rejected():
    pa = approvals.create("run-x", "1042", {"a": 1})
    ok, msg = approvals.resolve("run-x", "1042", True, "deadbeef00000000")
    assert not ok and "does not match" in msg  # X7
    ok, _ = approvals.resolve("run-x", "1042", True, pa.hash)
    assert ok


def test_summary_built_from_results_not_plan():
    r = run(BILLING, run_id="test-run-summary")
    text = slack_summary.build_summary(r)
    assert r["results"]["1042"]["paypal_id"] in text
    assert r["results"]["1043"]["jira_key"] in text
    assert "Billing run" in text
