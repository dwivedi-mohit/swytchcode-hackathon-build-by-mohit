"""LLM provider switch: gemini → groq failover → deterministic fallback.

Every node passes a `fallback` callable used when no provider is configured
or all providers fail (SECURITY E2), so the agent always makes progress.
MOCK_LLM=1 forces the fallback path with zero keys (tests / offline).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Callable

warnings: list[str] = []  # surfaced to the UI as amber log events


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def provider_chain() -> list[str]:
    if _env("MOCK_LLM") == "1":
        return []
    primary = _env("LLM_PROVIDER", "gemini").lower()
    order = [primary] + [p for p in ("gemini", "groq") if p != primary]
    chain = []
    for p in order:
        key = "GEMINI_API_KEY" if p == "gemini" else "GROQ_API_KEY"
        if _env(key):
            chain.append(p)
    return chain


def _extract_json(text: str) -> Any:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=0)
    end = max(text.rfind("}"), text.rfind("]"))
    if start != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _call(provider: str, system: str, user: str) -> Any:
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"), temperature=0
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq

        model = ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), temperature=0)
    else:
        raise RuntimeError(f"unknown provider {provider}")
    from langchain_core.messages import HumanMessage, SystemMessage

    resp = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return _extract_json(str(resp.content))


def llm_json(
    system: str,
    user: str,
    fallback: Callable[[], Any],
) -> tuple[Any, str]:
    """Returns (data, source) where source is 'gemini'|'groq'|'mock'.

    Never raises: on provider failure records a warning and uses `fallback`
    (E2/E12). MOCK_LLM=1 short-circuits to fallback.
    """
    for provider in provider_chain():
        try:
            return _call(provider, system, user), provider
        except Exception as exc:  # noqa: BLE001 — degrade, never crash (SECURITY §4)
            warnings.append(f"{provider} unavailable ({type(exc).__name__}: {exc}) → trying next")
    if provider_chain() == [] and _env("MOCK_LLM") != "1":
        warnings.append("no LLM key configured → deterministic fallback in use")
    return fallback(), "mock"
