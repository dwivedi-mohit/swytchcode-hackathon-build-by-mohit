# Security & Access Document

**Product:** LedgerPilot — AI Revenue Operations Agent
**Version:** v1.0 · **Date:** 25 September 2026
**Audience:** build team, mentors, jury

---

## 1. Authentication Method

LedgerPilot is a **local, single-operator tool**. There is deliberately no end-user login —
see PRD §8 (out of scope: multi-user accounts). Authentication therefore exists at three other
layers:

| Layer | Method | Where configured | Notes |
|---|---|---|---|
| **App access** | Localhost only — server binds `127.0.0.1` | `server/main.py` | Not reachable from the venue network unless explicitly bound to `0.0.0.0` (avoid during demo) |
| **Swytchcode integrations** | `swy login` / `swy auth <toolkit>` — CLI handles credential storage & refresh | Swytchcode CLI state (gitignored) | One-time per machine; no raw secrets in code or `.env` |
| **LLM providers** | API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) | `.env` (gitignored) | Never logged, never sent to the UI; only to provider endpoints |
| **External services** | Gmail OAuth test-user consent, PayPal sandbox client, Slack bot token, Notion integration secret, Jira API token | held by Swytchcode after auth | The app never writes these to disk itself |

**Rules:**

1. `.env` is in `.gitignore`; `.env.example` contains empty placeholders only.
2. The server refuses to start if a secret appears hardcoded (basic grep check in `setup.sh`).
3. PayPal is pinned to **sandbox** — no code path exists that can touch live money.
4. No authentication bypass "just for the demo" — if it isn't in this doc, it isn't built.

---

## 2. Roles & Permissions

The app has exactly **two actors**. This is the core of the security model:

### 2.1 The Agent (AI)

| Permission | Allowed? | Enforced by |
|---|---|---|
| Read Gmail (invoice search) | ✅ | Swytchcode `tooling.json` — `gmail` read tools enabled |
| Read Notion Ops DB | ✅ | enabled tools |
| **Write** Notion rows | ✅ | enabled tools (low-risk, reversible) |
| **Write** Jira issues | ✅ | enabled tools (low-risk, reversible) |
| **Write** Slack message to `#finance-ops` | ✅ | enabled tools (visible, reversible by delete) |
| **Write** PayPal (create/send invoice) | ⚠️ **Only after human approval** | **kernel policy `REQUIRES_APPROVAL` (`.swytchcode/integrations/policies.json`, `swy policy validate` ✓) + UI Approve button (both)** |
| Send email | ❌ not even enabled | tool never added to `tooling.json` |
| Read `.env` / print secrets | ❌ | code never exposes secrets to state, trace, or SSE |
| Touch any non-sandbox PayPal endpoint | ❌ | `PAYPAL_ENV=sandbox` + live path not implemented |
| Modify `policies.json` / `tooling.json` at runtime | ❌ | files read-only to the process after load |

**Principle of least privilege, in one sentence:** the agent may *observe* freely, may *record*
freely, but may *move value* only when a human clicks Approve — and the policy file makes that
gate a platform guarantee, not a prompt instruction.

### 2.2 The Human Approver (operator at the browser)

| Permission | Allowed? |
|---|---|
| Type prompts, approve/deny PayPal gates, view full trace | ✅ |
| Approve a *different* PayPal call than the one displayed | ❌ — approval binds to the exact request hash shown in the card |
| See secrets (keys, tokens) | ❌ — trace shows request/response bodies with `Authorization` redacted as `***` |
| Run multiple prompts concurrently | ❌ — UI locks Run while a stream is active |

### 2.3 Role summary table (quick view)

| Action | Agent alone | Agent + Approver | Nobody |
|---|---|---|---|
| Classify invoices, plan, summarize | ✅ | — | — |
| Create Notion row / Jira issue / Slack post | ✅ | — | — |
| Create or send PayPal invoice | ❌ | ✅ | — |
| Send raw email | — | — | ❌ (not built) |
| Live-money PayPal | — | — | ❌ (not built) |

---

## 3. Row-Level / Data-Scope Security

No SQL database exists, so RLS translates to **scope isolation across the connected services**:

| Store | Who can see it | Rule |
|---|---|---|
| **Notion Ops DB** | Only the workspace where the Notion integration was shared | Integration shared with **one database**, not the whole workspace. Agent cannot query other pages. |
| **Slack** | Members of `#finance-ops` only | Bot token scoped to a **private** channel created for the demo; agent may post to that channel only (`chat:write`, no `chat:write.public`) |
| **Gmail** | The operator's test mailbox | OAuth **test-user** consent, scope `gmail.readonly` (read, never modify/send) |
| **Jira** | The free Cloud site created for this project | API token scoped to one site; project key `OPS` only |
| **PayPal** | Sandbox accounts | Sandbox business + personal test accounts; zero real funds exist |
| **Trace UI** | Whoever has the browser | Bound to localhost; response payloads redact `Authorization`, cookies, and API keys before leaving the server |

**Cross-user isolation:** not applicable — there is one user (PRD §8). The demo mailbox,
workspace, and sandbox contain **test/dummy data only**, per event rules.

---

## 4. Error Handling Guide (every major failure point)

Design rule: **the app never crashes silently** — every failure becomes a visible trace card or
inline message, and the run degrades instead of dying.

| # | Failure point | Detection | User-facing response | System behavior |
|---|---|---|---|---|
| E1 | Empty / too-short prompt | Server-side validation (min 10 chars) | Inline red message: "Describe the billing task — e.g. 'Chase overdue invoices'" | No LLM or tool call made |
| E2 | Gemini key missing / quota exceeded | Provider exception | Trace card: "Primary LLM unavailable → switched to Groq" (amber) | Automatic failover to Groq; if both fail → MOCK_LLM message and halt with instructions |
| E3 | Gmail auth missing/expired | Swytchcode auth error on intake | Trace card: "Gmail not connected → reading seed invoices (demo data)" | `seed/invoices.json` intake; run continues normally; honesty label on every seed card |
| E4 | Gmail returns 0 invoices | Empty result set | Final answer: "No unpaid invoices found in `<query>`" + suggestion to broaden query | Writes skipped; run ends cleanly |
| E5 | PayPal API rejects (scope, network) | Exec error / non-2xx | Trace card status `failed`: "PayPal chase failed: `<reason>` — Notion and Slack will note the failure" | Retry once (Swytchcode idempotent retry); on second failure branch continues without PayPal |
| E6 | Approval denied by operator | UI Deny button | Trace card: "Chase cancelled by operator" | Invoice logged with `Status=SKIPPED`, Slack summary says cancelled |
| E7 | Approval never clicked (timeout 120 s) | Server timeout | Trace card: "Approval timed out — PayPal call not executed" | Same as E6, no partial state |
| E8 | Jira / Notion / Slack exec failure | Exec error | Amber card + `errors[]` entry; run continues | Final answer lists what was skipped |
| E9 | Venue network lost mid-run | SSE connection error / fetch failure | UI banner (amber): "Connection lost — retry or switch to hotspot"; Run re-enabled | Partial trace preserved; **backup video** offered in footer link |
| E10 | Duplicate prompt run (double-click, re-run) | Same `Run ID` + idempotency key | Normal run; PayPal/Jira receive idempotency key | Swytchcode idempotency prevents duplicate chase — response returns original object |
| E11 | LLM returns malformed invoice JSON | Schema parse failure | Card: "Could not parse invoice `<n>` — skipped with note" | Remaining invoices processed |
| E12 | Rate limit on provider | 429 | Amber card + 3 s backoff, one retry, then Groq failover | Run continues |
| E13 | Someone opens UI from another machine | Connection refused | N/A — server binds localhost | By design (§1) |
| E14 | Secret accidentally staged for commit | `setup.sh` pre-commit grep + `.gitignore` | Build aborts with list of offending files | Nothing sensitive pushed |

---

## 5. Edge Cases (the weird stuff)

| # | Edge case | Defined behavior |
|---|---|---|
| X1 | Prompt with no invoice verbs ("hi") | `plan` classifies as `read_only` + no-op: agent answers conversationally, zero tool calls |
| X2 | Invoice marked DISPUTED **and** overdue | DISPUTED wins — Jira escalation only; PayPal explicitly skipped (trace shows the reason) |
| X3 | Same invoice appears twice in intake | Deduped by invoice ID before classify; second occurrence dropped with note |
| X4 | Invoice amount unparseable | Amount set to `null` → label falls back to `DUE_SOON`/`log_only`; card flags "amount unknown" |
| X5 | Operator approves, then reloads page mid-run | Server run continues; on reload, UI reconnects to SSE and replays buffered events for active run (or shows last run summary) |
| X6 | Slow connection (payload > 5 s) | SSE events are small JSON; UI shows per-card skeleton with spinner; no blocking preloader |
| X7 | PayPal approval clicked twice rapidly | Server accepts first approval only; request-hash match required; second is ignored |
| X8 | Prompt asks to exceed `MAX_INVOICES` (e.g., "all 500 invoices") | Agent processes first 10, states truncation in final answer |
| X9 | Slack channel missing | Exec fails → E8 path; final answer renders the summary inline as fallback text |
| X10 | Notion DB deleted before run | E8 path; run continues, final answer says "log unavailable — summary below" |
| X11 | Judge pastes a prompt from another track ("post to Telegram") | Agent honestly replies: "Not among my connected toolkits (gmail, paypal, jira, notion, slack)" — no hallucinated calls |
| X12 | Empty `decisions[]` (all invoices PAID) | Skips write nodes entirely; final answer: "Nothing to chase — 4 invoices all settled" |

---

## 6. Audit & Evidence (for Q&A)

- **`tooling.json`** committed → shows exactly which toolkits/tools are enabled.
- **`.swytchcode/integrations/policies.json`** (kernel-enforced, `swy policy list`) + evidence
  copy `.swytchcode/policies.json` → PayPal approval / Gmail read-only / no live money
  (verifiable by judges with `swy policy validate`).
- **`swy audit`** available live → proves every call went through Swytchcode's execution layer.
- **Full `trace`** per run, optionally dumped to JSON → screenshots for README.
- **Redaction:** `Authorization` fields rendered as `***` in trace/UI before display.

---

*Companions: `PRD.md` §8 (scope boundaries), `TECHNICAL_ARCHITECTURE.md` §5 (env), `DEMO_SCRIPT.md`
(E5/E6/E9 appear in the pitch as "what happens if PayPal fails").*
