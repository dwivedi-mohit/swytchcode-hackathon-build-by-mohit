"""In-process event bus: nodes publish trace events; SSE streams them live."""
from __future__ import annotations

import queue
import threading
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: dict[str, list[queue.Queue]] = {}
        self._history: dict[str, list[dict]] = {}

    def subscribe(self, run_id: str) -> tuple[queue.Queue, list[dict]]:
        """Returns (queue, history_snapshot) for replay-on-connect (edge X5)."""
        q: queue.Queue = queue.Queue()
        with self._lock:
            history = list(self._history.get(run_id, []))
            self._subs.setdefault(run_id, []).append(q)
        return q, history

    def unsubscribe(self, run_id: str, q: queue.Queue) -> None:
        with self._lock:
            subs = self._subs.get(run_id, [])
            if q in subs:
                subs.remove(q)

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            self._history.setdefault(run_id, []).append(event)
            subs = list(self._subs.get(run_id, []))
        for q in subs:
            q.put(event)

    def history(self, run_id: str) -> list[dict]:
        with self._lock:
            return list(self._history.get(run_id, []))

    def prune(self, run_id: str) -> None:
        with self._lock:
            self._subs.pop(run_id, None)
            self._history.pop(run_id, None)


bus = EventBus()
