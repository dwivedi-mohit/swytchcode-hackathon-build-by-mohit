# Demo Script — 2.5-Minute Pitch + Live Run

**Product:** LedgerPilot — AI Revenue Operations Agent
**Version:** v1.0 · **Date:** 25 September 2026
**Audience:** jury (6 criteria, 30% Swytchcode integration) + Q&A
**Total budget:** 2 min 30 s scripted pitch, ≤3 min with the live run (Gate F in `BUILD.md`)

---

## 0. Before you walk up

| Check | State |
|---|---|
| `python -m server.main` already running | ✅ terminal hidden behind browser |
| Browser on `http://localhost:8000`, zoom 110%, fullscreen (F11) | ✅ |
| Trace UI empty state visible | ✅ |
| Backup video tab open in background (`docs/demo/run.mp4`) | ✅ |
| Phone hotspot on, laptop wifi verified with one Swytchcode call | ✅ |
| `.env` loaded — Gemini primary confirmed (check terminal for provider line) | ✅ |
| Demo prompt #1 pre-typed in a notes file for one-paste | ✅ |

**Fallback ladder if the live run breaks:** finish the narrated run on the seeded/trace state →
if it dies completely → play backup video while narrating → never apologize, state the
degradation (SECURITY E9) and move on.

---

## 1. The script (say it, adapt wording freely)

### Hook — 0:00–0:20
> "Every small business does billing day by hand: dig through email, chase whoever is late,
> file disputes somewhere, log it, tell the team. LedgerPilot is an **agent that does that whole
> loop** — and shows its work, call by call, while it happens.
>
> It's built on **LangGraph** state machines over the **Swytchcode runtime**, with five
> connected toolkits: **Gmail, PayPal, Jira, Notion, Slack**."

*(Point at header pill: "5 toolkits connected".)*

### Prompt — 0:20–0:35
Type/paste demo prompt #1 into the box:

> "It's billing day. Find unpaid invoices, chase overdue ones with PayPal, escalate disputes to
> Jira, log everything to Notion, and summarize in Slack."

> "Watch what the agent does with that — one sentence in, a full plan out."

**Hit Run.** Do not narrate silence — go straight to the trace.

### Live narration — 0:35–2:15 *(follow the cards as they appear)*

| Card | Say (≈10 s each) |
|---|---|
| `plan` | "First it *plans* — this is a write-mode task, so it queues intake, classification, then the writes. It reasons this with the LLM, not hard-coded keywords." |
| `intake` (gmail) | "It pulls invoice emails through **Swytchcode's Gmail toolkit** and parses them into structured invoices." *(if seed mode: "— running on seed demo data because Gmail auth is scoped to my mailbox; the pill says DEMO DATA, we're honest about it.")* |
| `classify` | "Now it *decides* per invoice: overdue, disputed, due soon, paid — each with a reason. **The dispute wins over overdue** — no payment chase on a contested invoice." |
| **`paypal_chase` — approval card** | "**This is the key security moment.** PayPal is money, so the agent *can't* just act. `policies.json` requires human approval — the exact request is on screen. I approve…" *(click Approve)* "…and only now does the Swytchcode call fire — sandbox, idempotency-keyed." |
| `jira_escalate` | "The disputed invoice goes the *other* branch — a Jira issue with priority derived from the amount. PayPal was skipped for it, by design." |
| `notion_log` | "Every outcome lands in the **Notion** ops log — status taken from the *actual* API responses, not from what the plan hoped would happen." |
| `slack_summary` | "Finally it composes a summary from the real results and posts to **Slack** `#finance-ops`." |
| Final answer | "And the operator gets the plain-language result — with the PayPal ID, the Jira key, the row count — plus every step above as an audit trail." |

### Close — 2:15–2:30
> "Three things to remember: **five Swytchcode toolkits chained** — each output feeds the next
> step; a **real approval policy** so an AI can't move money alone; and **honest degradation** —
> kill a service and it falls back to seed data or logs the failure instead of pretending.
> The repo, README, and architecture diagram are in our Commudle submission. LedgerPilot —
> revenue ops that shows its work."

---

## 2. The 3 demo prompts (keep visible)

| # | Prompt | Proves |
|---|---|---|
| 1 | *It's billing day. Find unpaid invoices, chase overdue ones with PayPal, escalate disputes to Jira, log everything to Notion, and summarize in Slack.* | full chain, approval gate |
| 2 | *Only chase invoices over ₹50,000.* | parameterized intent → fewer branches fire |
| 3 | *What did we chase this week?* | read-only mode — zero write calls (SECURITY §2.1) |

**Order in a live demo:** #1 always. #2 or #3 only if the jury asks or time remains.

---

## 3. Likely Q&A — 30-second answers

| Question | Answer |
|---|---|
| "How does it know when to use PayPal vs Jira?" | "The LLM classifies each invoice with a reason — DISPUTED → Jira only, OVERDUE → PayPal + log — and the graph's conditional edges enforce it. There's an assert in the test proving disputed invoices never reach PayPal." |
| "What stops it from sending 500 payments?" | "Three things: `policies.json` human approval, `MAX_INVOICES` cap, and idempotency keys so a re-run can't double-chase." |
| "What if Gmail/Slack goes down mid-run?" | "Every failure path is defined: seed intake, skip-and-note, inline summary fallback — the run degrades, it never dies with a stack trace." |
| "Why LangGraph?" | "The workflow has branches, a human-in-the-loop pause, and a fan-in — that's state-machine territory. Conditional edges plus a checkpointer give us resume-after-approval cleanly." |
| "Where's the Swytchcode magic?" | "`swx.tools.execute` is the only path to any service — canonical IDs in `tooling.json`, structured validated responses, audit trail. The agent never does raw HTTP." |
| "Is real money involved?" | "No — PayPal is pinned to sandbox; the policy gate would still be required in production." |
| "Solo? What's your stack?" | "Python, LangGraph, FastAPI + SSE, one-file UI. Yes, solo." |

---

## 4. Timeline at a glance

```
0:00 ── hook
0:20 ── paste prompt, Run
0:35 ── narrate cards (plan → intake → classify)
1:10 ── APPROVAL GATE click (the money moment)
1:25 ── jira → notion → slack → final answer
2:15 ── closing line
2:30 ── Q&A
```

**Practice:** full dry-run with timer at least twice before the pitch (Gate F). If over 3:00,
cut prompt #2/#3 — never cut the approval-gate narration.
