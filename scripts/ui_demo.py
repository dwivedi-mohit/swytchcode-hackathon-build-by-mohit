#!/usr/bin/env python3
"""Browser E2E of the LedgerPilot UI: click-through run + screenshots + video.

Verifies the UI end-to-end (Gate D, browser level):
  load page → chip → Run → stream cards → approval card → Approve → final answer

Usage:  python scripts/ui_demo.py
Needs:  pip install playwright && playwright install chromium
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = os.getenv("DEMO_PORT", "8123")
BASE = f"http://127.0.0.1:{PORT}"
SHOTS = ROOT / "docs" / "screenshots"
DEMO = ROOT / "docs" / "demo"
FAILURES: list[str] = []


def check(cond: bool, what: str) -> None:
    mark = "✓" if cond else "✗"
    print(f"  {mark} {what}", flush=True)
    if not cond:
        FAILURES.append(what)


def wait_server(timeout_s: float = 20) -> bool:
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            with urllib.request.urlopen(BASE + "/healthz", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main() -> int:
    sys.path.insert(0, str(ROOT))
    SHOTS.mkdir(parents=True, exist_ok=True)
    DEMO.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "MOCK_LLM": "1", "MOCK_SWX": "1", "GMAIL_ENABLED": "0",
           "PORT": PORT, "HOST": "127.0.0.1"}
    env.pop("AUTO_APPROVE", None)  # the UI must perform a real approval
    env.pop("APPROVAL_TIMEOUT_S", None)
    server = subprocess.Popen(
        [sys.executable, "-m", "server.main"], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_server():
            print("✗ server did not start", flush=True)
            return 1
        return run_browser()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


def run_browser() -> int:
    from playwright.sync_api import sync_playwright

    print("\nBrowser E2E →", BASE, flush=True)
    video_tmp = DEMO / "_video_tmp"
    if video_tmp.exists():
        shutil.rmtree(video_tmp)
    video_tmp.mkdir(parents=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                  record_video_dir=str(video_tmp),
                                  record_video_size={"width": 1280, "height": 800})
        page = ctx.new_page()

        # 1 — load
        page.goto(BASE, wait_until="networkidle")
        check(page.locator("header h1").inner_text() == "LedgerPilot", "header renders")
        pill = page.locator("#statusPill").inner_text()
        check("toolkits" in pill, f"status pill: {pill}")
        check(page.locator("#empty").is_visible(), "empty state visible")
        page.screenshot(path=str(SHOTS / "01-prompt.png"))

        # 2 — chip + run
        page.click("text=Billing day (full run)")
        prompt = page.locator("#prompt").input_value()
        check("billing day" in prompt.lower(), "chip fills prompt")
        page.screenshot(path=str(SHOTS / "02-prompt-filled.png"))

        page.click("#runBtn")
        page.wait_for_selector(".card", timeout=15000)
        check(page.locator("#runBtn").is_disabled(), "Run disabled while streaming")

        # 3 — cards stream in
        page.wait_for_selector(".card.approval", timeout=30000)
        check(page.locator(".card").count() >= 3, f"{page.locator('.card').count()} cards streamed")
        reasoning = page.locator(".card").first.locator(".reasoning").inner_text()
        check(len(reasoning) > 10, "first card has reasoning text")
        page.screenshot(path=str(SHOTS / "03-streaming.png"), full_page=True)

        # 4 — approval card specifics
        appr = page.locator(".card.approval")
        check("pending approval" in appr.inner_text().lower()
              or appr.locator(".pill").count() > 0, "approval card shows pending state")
        check(appr.locator(".btn-approve").is_visible(), "Approve button visible")
        check(appr.locator(".btn-deny").is_visible(), "Deny button visible")
        check("policies.json" in appr.inner_text(), "policy note shown")
        page.screenshot(path=str(SHOTS / "04-approval.png"), full_page=True)

        # 5 — approve and finish
        appr.locator(".btn-approve").click()
        page.wait_for_selector("#final.show", timeout=60000)
        final = page.locator("#finalBody").inner_text()
        check("INV-" in final, "final answer has PayPal ID")
        check("OPS-" in final, "final answer has Jira key")
        check("Notion Ops Log" in final, "final answer mentions Notion rows")

        # 6 — whole trace rendered
        n_cards = page.locator(".card").count()
        check(n_cards >= 8, f"{n_cards} trace cards rendered")
        page.screenshot(path=str(SHOTS / "05-final.png"), full_page=True)

        # 7 — denied path (second run via "Run again", Deny button)
        page.click("#final >> text=Run again")
        page.wait_for_selector(".card.approval .btn-deny", timeout=30000)
        page.locator(".card.approval .btn-deny").click()
        page.wait_for_selector("#final.show", timeout=60000)
        f2 = page.locator("#finalBody").inner_text()
        check("skipped" in f2.lower() or "not approved" in f2.lower(),
              "deny → invoice skipped in final answer")
        page.screenshot(path=str(SHOTS / "06-denied.png"), full_page=True)

        # video artifact
        video = page.video
        ctx.close()
        vpath = video.path()
        browser.close()
        target = DEMO / "run.mp4"
        shutil.move(str(vpath), str(target))
        check(target.exists() and target.stat().st_size > 10_000,
              f"video recorded ({target.stat().st_size // 1024} KB)")

    print("\nScreenshots →", SHOTS)
    if FAILURES:
        print(f"\nUI E2E FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print("  ✗", f)
        return 1
    print("\nUI E2E PASSED — Gate D (browser level)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
