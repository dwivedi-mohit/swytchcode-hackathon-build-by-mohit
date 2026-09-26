"""CLI contract test — verifies the exact `swy exec` invocation shape offline (A1).

The live kernel can't run here (registry egress-blocked), so we assert the
subprocess contract: stdin JSON {"tool","args"}, --json flag, repeatable
--header k=v. Matches `swytchcode exec --help` v2.23.7 (help mode #2).
"""
from __future__ import annotations

import json
import subprocess

from agent import swx


def _fake_run(cmd, input=None, capture_output=True, text=True, timeout=None, **kw):
    assert cmd[:2] == ["swy", "exec"], cmd
    assert "--json" in cmd, "--json flag missing"
    # headers appended as repeated --header k=v
    headers = {}
    for i, part in enumerate(cmd):
        if part == "--header":
            k, v = cmd[i + 1].split("=", 1)
            headers[k] = v
    spec = json.loads(input)
    assert set(spec) == {"tool", "args"}, f"stdin spec keys wrong: {set(spec)}"
    return subprocess.CompletedProcess(cmd, 0,
                                       stdout=json.dumps({"ok": True, "echo": spec["tool"]}),
                                       stderr="")


def test_cli_invocation_contract(monkeypatch):
    monkeypatch.setattr(swx.subprocess, "run", _fake_run)
    monkeypatch.setattr(swx, "_sdk_available", lambda: False)
    monkeypatch.setattr(swx, "_cli_present", lambda: True)

    out = swx._live_execute("invoices.invoicing.send.create",
                            {"invoice": {"number": "INV-1"}},
                            {"Idempotency-Key": "run1:1042:invoices.invoicing.send.create"})
    assert out == {"ok": True, "echo": "invoices.invoicing.send.create"}


def test_execute_live_passes_headers_not_body(monkeypatch):
    seen = {}

    def spy(cmd, input=None, **kw):
        seen["cmd"] = cmd
        seen["input"] = json.loads(input)
        return subprocess.CompletedProcess(cmd, 0, stdout='{"id":"INV-1"}', stderr="")

    monkeypatch.setattr(swx.subprocess, "run", spy)
    monkeypatch.setattr(swx, "mode", lambda: "live")
    monkeypatch.setattr(swx, "_sdk_available", lambda: False)

    res = swx.execute("invoices.invoicing.send.create", {"invoice": {"number": "INV-1"}},
                      run_id="r1", invoice_id="1042", write=True)
    assert res["ok"] and res["mode"] == "live"
    assert "Idempotency-Key" not in seen["input"]["args"], "idempotency must be a header"
    assert any("Idempotency-Key=r1:1042:invoices.invoicing.send.create" in p for p in seen["cmd"])
    assert seen["input"]["args"] == {"invoice": {"number": "INV-1"}}


def test_cli_error_mentions_setup_hint(monkeypatch):
    def fail(cmd, input=None, **kw):
        return subprocess.CompletedProcess(cmd, 1, stdout="",
                                           stderr="× Failed to fetch provider bundles. hint: check network")

    monkeypatch.setattr(swx.subprocess, "run", fail)
    monkeypatch.setattr(swx, "_sdk_available", lambda: False)
    monkeypatch.setattr(swx, "mode", lambda: "live")  # other test modules set MOCK_SWX

    res = swx.execute("gmail.user.messages.get", {"q": "x"}, run_id="r", invoice_id="", write=False)
    assert not res["ok"]
    assert "scripts/setup.sh" in res["error"], "actionable hint missing"
