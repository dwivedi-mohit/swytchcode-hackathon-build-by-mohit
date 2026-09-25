"""Run orchestration: background graph execution + SSE formatting."""
from __future__ import annotations

import json
import threading
import traceback
from typing import Optional

from agent import approvals, graph
from agent.events import bus

# single run at a time (arch §7)
_active: dict[str, object] = {}
_lock = threading.Lock()


def active_run() -> Optional[str]:
    with _lock:
        return next(iter(_active), None)


def is_active(run_id: str) -> bool:
    with _lock:
        return run_id in _active


def start_run(run_id: str, prompt: str) -> None:
    with _lock:
        if _active:
            raise RuntimeError("a run is already in progress")
        _active[run_id] = True

    def _worker() -> None:
        try:
            final = graph.run(prompt, run_id)
            bus.publish(
                run_id,
                {
                    "type": "done",
                    "run_id": run_id,
                    "final_answer": final.get("final_answer", ""),
                    "errors": final.get("errors", []),
                    "steps": len(final.get("trace", [])),
                },
            )
        except Exception as exc:  # noqa: BLE001 — surface, never crash the server
            bus.publish(
                run_id,
                {
                    "type": "error",
                    "run_id": run_id,
                    "text": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(limit=3),
                },
            )
        finally:
            approvals.clear(run_id)
            with _lock:
                _active.pop(run_id, None)

    threading.Thread(target=_worker, name=f"run-{run_id}", daemon=True).start()


def sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
