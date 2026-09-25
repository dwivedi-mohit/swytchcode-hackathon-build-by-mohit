"""API E2E: POST /run → SSE stream → approval endpoint → done (T31 verification)."""
from __future__ import annotations

import json
import os

import pytest

os.environ["MOCK_LLM"] = "1"
os.environ["MOCK_SWX"] = "1"
os.environ["GMAIL_ENABLED"] = "0"
os.environ["AUTO_APPROVE"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from server.main import app  # noqa: E402

BILLING = (
    "It's billing day. Find unpaid invoices, chase overdue ones with PayPal, "
    "escalate disputes to Jira, log everything to Notion, and summarize in Slack."
)

client = TestClient(app)


def _events(run_id: str) -> list[dict]:
    out = []
    with client.stream("GET", f"/stream/{run_id}") as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("data: "):
                out.append(json.loads(line[6:]))
                if out[-1].get("type") in ("done", "error"):
                    break
    return out


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "gmail" in body["toolkits"] and "paypal" in body["toolkits"]


def test_empty_prompt_rejected():
    r = client.post("/run", json={"prompt": "hi"})
    assert r.status_code == 400  # E1 — no LLM call made


def test_full_run_streams_and_completes():
    r = client.post("/run", json={"prompt": BILLING})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    events = _events(run_id)
    types = [e["type"] for e in events]
    assert "approval" in types, "approval card must stream"
    assert types[-1] == "done"
    done = events[-1]
    assert "INV-" in done["final_answer"] and "OPS-" in done["final_answer"]

    nodes = [e.get("node") for e in events if e.get("type") in ("trace", "approval")]
    assert nodes and nodes[0] == "plan"


def test_replay_on_reconnect_no_duplicates():
    r = client.post("/run", json={"prompt": BILLING})
    run_id = r.json()["run_id"]
    first = _events(run_id)
    second = _events(run_id)  # history replay (X5)
    assert len(first) == len(second)
    steps1 = [e.get("step") for e in first if e.get("type") in ("trace", "approval")]
    assert len(steps1) == len(set(steps1)), "duplicate cards on replay"


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "LedgerPilot" in r.text
