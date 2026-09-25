"""LedgerPilot API — POST /run, GET /stream/{run_id}, POST /approve, /healthz.

Binds 127.0.0.1 only (SECURITY §1). The UI consumes SSE exclusively.
Run:  python -m server.main   →  http://localhost:8000
"""
from __future__ import annotations

import asyncio
import os
import queue
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import approvals
from agent.events import bus
from agent import swx

from . import stream

app = FastAPI(title="LedgerPilot", version="1.0.0")
UI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")


class RunRequest(BaseModel):
    prompt: str


class ApprovalRequest(BaseModel):
    run_id: str
    invoice_id: str
    approved: bool
    request_hash: str


@app.post("/run")
def start_run(req: RunRequest):
    prompt = req.prompt.strip()
    if len(prompt) < 10:  # E1 — validation before any LLM/tool call
        raise HTTPException(400, "Describe the billing task — e.g. 'Chase overdue invoices'")
    if stream.active_run():
        raise HTTPException(409, "A run is already in progress — wait for it to finish")
    run_id = uuid.uuid4().hex[:12]
    stream.start_run(run_id, prompt)
    return {"run_id": run_id}


@app.post("/approve")
def approve(req: ApprovalRequest):
    ok, msg = approvals.resolve(req.run_id, req.invoice_id, req.approved, req.request_hash)
    if not ok:
        raise HTTPException(409, msg)
    return {"ok": True, "message": msg}


@app.get("/stream/{run_id}")
async def stream_run(run_id: str):
    q, history = bus.subscribe(run_id)

    async def gen():
        try:
            for ev in history:  # replay for reconnects (X5)
                yield stream.sse(ev)
            if any(ev.get("type") == "done" for ev in history) or any(
                ev.get("type") == "error" for ev in history
            ):
                return
            while True:
                try:
                    ev = await asyncio.to_thread(q.get, True, 15.0)
                except queue.Empty:
                    yield ": ping\n\n"  # keep-alive through venue wifi
                    continue
                yield stream.sse(ev)
                if ev.get("type") in ("done", "error"):
                    return
        finally:
            bus.unsubscribe(run_id, q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "swx_mode": swx.mode(),
        "llm": "mock" if os.getenv("MOCK_LLM") == "1" else os.getenv("LLM_PROVIDER", "gemini"),
        "toolkits": list(_toolkits()),
        "active_run": stream.active_run(),
    }


def _toolkits() -> list:
    import json as _json
    from pathlib import Path

    p = Path(__file__).resolve().parents[1] / ".swytchcode" / "tooling.json"
    try:
        return list(_json.loads(p.read_text())["toolkits"].keys())
    except Exception:
        return []


@app.get("/")
def index():
    return FileResponse(os.path.join(UI_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
