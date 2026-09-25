# Feature Ticket List (Build Checklist)

**Product:** LedgerPilot — AI Revenue Operations Agent
**Version:** v1.0 · **Date:** 25 September 2026
**How to use:** each ticket is written to be pasted directly into an AI coding tool as a prompt.
Work top-to-bottom — dependencies are ordered. Priority: **MUST** (launch/demo floor),
**SHOULD** (resilience/polish), **NICE** (bonus).

**Build order legend:** 🟦 Phase 0 = tonight's prep · 🟩 Phase 1 = scaffold (with mock) ·
🟨 Phase 2 = live integrations (on-site) · 🟪 Phase 3 = demo-ready & submission

---

## Phase 0 — Platform & credentials (before any agent code)

### T01 — Swytchcode project setup script
**Priority:** MUST · **Depends on:** — · **Phase:** 🟦

**Task:** Create `scripts/setup.sh` that: runs `swy init` (non-interactive), `swy get` for
`paypal gmail slack jira notion`, `swy add` the canonical tools listed in
`FRONTEND_SPEC.md §6`, prints `swy doctor` at the end, and fails loudly with a clear message
on any error. Also verify no secret is hardcoded anywhere (grep for `key|token|secret` in tracked
files) before finishing.

**Acceptance criteria:**
- [ ] Fresh clone + `./scripts/setup.sh` results in `.swytchcode/tooling.json` listing all 5 toolkits
- [ ] Script exits non-zero with a readable error if any `swy` command fails
- [ ] Script ends with a "next steps" printout (auth commands + smoke test)

---

### T02 — Toolkit smoke test
**Priority:** MUST · **Depends on:** T01 · **Phase:** 🟦

**Task:** Create `scripts/smoke_test.py` that executes exactly one benign call per toolkit
(gmail list, PayPal draft read/create in sandbox, Jira metadata or create-in-project, Notion
DB query, Slack `chat.postMessage` to `#finance-ops`), prints a PASS/FAIL matrix table with
latency per call, and exits 1 if fewer than 3 toolkits pass.

**Acceptance criteria:**
- [ ] Output clearly shows per-toolkit PASS/FAIL + ms
- [ ] Floor of 3 passing toolkits enforced (exit code)
- [ ] Runs without the agent codebase (standalone)

---

## Phase 1 — Scaffold with mock E2E (works without any keys)

### T11 — Project skeleton
**Priority:** MUST · **Depends on:** T01 · **Phase:** 🟩

**Task:** Create the full folder structure from `TECHNICAL_ARCHITECTURE.md §3` with empty
modules, `requirements.txt` (`langgraph`, `langchain-core`, `langchain-google-genai`,
`langchain-groq`, `fastapi`, `uvicorn`, `python-dotenv`, `swytchcode_runtime`, `pytest`),
`.env.example` exactly as in `TECHNICAL_ARCHITECTURE.md §5`, and `.gitignore` covering `.env`,
`__pycache__`, `.swytchcode/*auth*`, `docs/demo/*.mp4`.

**Acceptance criteria:**
- [ ] Tree matches the architecture doc exactly
- [ ] `pip install -r requirements.txt` succeeds
- [ ] No secret material in tracked files

---

### T12 — State schema
**Priority:** MUST · **Depends on:** T11 · **Phase:** 🟩

**Task:** Implement `agent/state.py`: `InvoiceState` TypedDict per
`TECHNICAL_ARCHITECTURE.md §4.1`, plus `Invoice`, `Decision`, and `TraceEvent` dataclasses/
TypedDicts with `to_dict()` helpers. Include `new_trace_event()` factory that fills `step`,
`ts`, and redacts `Authorization` → `***`.

**Acceptance criteria:**
- [ ] All fields from the architecture doc exist with correct types
- [ ] Redaction unit-checked: an event containing `Authorization` serializes as `"***"`
- [ ] Trace event JSON shape matches `FRONTEND_SPEC.md §4.4`

---

### T13 — LLM provider switch (gemini | groq | mock)
**Priority:** MUST · **Depends on:** T11 · **Phase:** 🟩

**Task:** Implement `agent/llm.py`: `get_llm()` returns a chat model based on `LLM_PROVIDER`,
with automatic failover (Gemini error/429 → Groq, both fail → clear RuntimeError mentioning
`MOCK_LLM=1`). Implement `MockChatModel` that classifies invoices by keyword rules
(contains "overdue"/days-past → OVERDUE; contains "dispute" → DISPUTED; "paid" → PAID;
else DUE_SOON) and produces a fixed plan for the billing-day prompt.

**Acceptance criteria:**
- [ ] `MOCK_LLM=1` works with zero keys installed
- [ ] Failover emits a warning event usable by the UI (SECURITY E2)
- [ ] Mock produces deterministic output — running twice gives identical decisions

---

### T14 — Seed intake + Gmail intake node
**Priority:** MUST (seed) / MUST (gmail, degraded-ok) · **Depends on:** T12, T13 · **Phase:** 🟩

**Task:** Create `seed/invoices.json` (4 invoices exactly as in
`TECHNICAL_ARCHITECTURE.md §4.4`) and `agent/nodes/intake.py`: if `GMAIL_ENABLED=1` and auth
works, search+fetch via Swytchcode gmail tools and parse to `Invoice[]` (LLM-assisted); on any
auth/availability error, load the seed file and tag every invoice `email_ref="seed"`. Always
dedupe by invoice id (X3), cap at `MAX_INVOICES` (X8).

**Acceptance criteria:**
- [ ] With no Gmail auth: run still produces 4 invoices and the trace shows a `seed` pill
- [ ] Duplicates removed; cap respected with truncation note
- [ ] Parsing failure of one email doesn't kill the run (E11)

---

### T15 — Plan + classify nodes
**Priority:** MUST · **Depends on:** T13, T14 · **Phase:** 🟩

**Task:** Implement `agent/nodes/plan.py` (interpret prompt → `mode` ∈ {write, read_only} +
ordered `plan[]`; conversational no-op prompts → read_only per X1) and
`agent/nodes/classify.py` (LLM labels each invoice OVERDUE/DISPUTED/DUE_SOON/PAID with a
one-line reason; DISPUTED dominates overdue per X2; unparseable amount → log_only per X4).
Each node appends a TraceEvent with reasoning, toolkit=`none` for LLM-only steps.

**Acceptance criteria:**
- [ ] Billing-day prompt yields exactly one OVERDUE, one DISPUTED, one DUE_SOON, one PAID on seed data
- [ ] Prompt 3 ("What did we chase…") classifies mode=read_only
- [ ] Every invoice has a decision with a reason string

---

### T16 — Action nodes: paypal_chase, jira_escalate, notion_log, slack_summary, respond
**Priority:** MUST · **Depends on:** T15 · **Phase:** 🟩 (mock tools) / 🟨 (live)

**Task:** Implement the five nodes per `TECHNICAL_ARCHITECTURE.md §6`, each following the same
contract: read state → call Swytchcode via `agent/swx.py` → append TraceEvent
(toolkit, canonical_id, request, response, decision) → write `results` → never raise past the
graph (E5/E8). `paypal_chase` must set `approval_pending` and wait for approval before
executing; `jira_escalate` must never call PayPal; `slack_summary` must build its text from
`results`, not the plan; `respond` assembles `final_answer` including `errors[]`.

**Acceptance criteria:**
- [ ] With a mocked `swx.execute`, one run produces the full 7-card trace
- [ ] Disputed invoice path provably contains zero PayPal calls (assert in test)
- [ ] Slack text contains the mock PayPal ID and Jira key
- [ ] A failing tool in one branch leaves the rest of the run intact

---

### T17 — Graph assembly + conditional edges
**Priority:** MUST · **Depends on:** T16 · **Phase:** 🟩

**Task:** Implement `agent/graph.py` building the LangGraph `StateGraph` exactly as the table in
`TECHNICAL_ARCHITECTURE.md §6`: edges plan→intake→classify; conditional classify→
(paypal_chase | jira_escalate | notion_log) fan-in to notion_log→slack_summary→respond;
read_only route skips all writes; `MemorySaver` checkpointer; `run_graph(prompt, emit)` API
that yields trace events as they are produced.

**Acceptance criteria:**
- [ ] Visual/ASCII dump of the graph matches the architecture doc
- [ ] Same seed data + billing prompt → PayPal AND Jira branches both execute
- [ ] read_only prompt executes zero write nodes (assert)

---

### T18 — E2E mock test
**Priority:** MUST · **Depends on:** T17 · **Phase:** 🟩

**Task:** Create `tests/test_graph.py` running the full billing-day prompt under `MOCK_LLM=1`
with a fake `swx.execute`, asserting: (a) ≥6 trace events with toolkits
{gmail/seed, paypal, jira, notion, slack}; (b) approval_pending honored (event status
`pending_approval` then `approved` when approval provided); (c) disputed invoice has no PayPal
event; (d) final_answer mentions PayPal ID + Jira key; (e) read-only run has no write events.

**Acceptance criteria:**
- [ ] `pytest` green with no network and no keys
- [ ] Runtime < 10 s
- [ ] Failure messages name the missing behavior, not a stack trace

---

## Phase 2 — Live integrations & policy (on-site)

### T21 — Swytchcode wrapper with idempotency + redaction
**Priority:** MUST · **Depends on:** T16 · **Phase:** 🟨

**Task:** Finalize `agent/swx.py`: singleton Swytchcode client, `execute(canonical_id, params,
run_id, invoice_id=None)` attaching `Idempotency-Key` for writes, translating tool errors into
`ToolError(reason, retryable)`, applying one automatic retry for retryable errors (E5), and
redacting secrets from any payload before it enters state.

**Acceptance criteria:**
- [ ] Same write executed twice with same key → second is a no-op/returns original (verify against a live tool)
- [ ] No `Authorization` value ever appears in state, logs, or SSE

---

### T22 — Approval gate: policies.json + UI approval round-trip
**Priority:** MUST · **Depends on:** T21, T31 · **Phase:** 🟨

**Task:** Write `.swytchcode/policies.json` requiring human approval for `paypal.*` writes;
wire the round-trip: graph pauses at `approval_pending` → SSE emits approval card → UI
Approve/Deny → server validates the approval matches the request hash (X7) → graph resumes or
cancels (E6), with 120s timeout (E7).

**Acceptance criteria:**
- [ ] PayPal call **cannot** execute without approval — verify by calling exec directly (policy rejects)
- [ ] Deny → invoice logged as SKIPPED, Slack notes cancellation
- [ ] Double-click approve accepted once; timeout path covered by test

---

### T23 — Live Gmail intake
**Priority:** SHOULD · **Depends on:** T14, T21 · **Phase:** 🟨

**Task:** Complete Google Cloud setup (enable Gmail API, OAuth consent = Testing, test user),
auth via Swytchcode, send 4 self-addressed seed emails matching `seed/invoices.json`, verify
`GMAIL_ENABLED=1` intake returns them with the same shapes as seed.

**Acceptance criteria:**
- [ ] Live run and seed run produce identical `Invoice[]` shapes
- [ ] Toggle `GMAIL_ENABLED=0` reverts cleanly (E3)
- [ ] Zero write scopes on the Gmail credential

---

### T24 — Live PayPal / Jira / Notion / Slack wiring
**Priority:** MUST (paypal+slack+notion) / SHOULD (jira) · **Depends on:** T21, T22 · **Phase:** 🟨

**Task:** Auth all four through `swy`, run `smoke_test.py`, then execute one full live run;
record actual canonical IDs and response shapes back into `FRONTEND_SPEC.md §6`
("illustrative" → confirmed). If PayPal invoice API is unavailable, pivot node to the closest
available PayPal action without changing the graph.

**Acceptance criteria:**
- [ ] ≥3 toolkits PASS smoke test on venue Wi-Fi (floor), target 5
- [ ] One complete live run: real PayPal sandbox ID + Jira key + Notion page + Slack `ts`
- [ ] Spec docs updated with confirmed canonical IDs

---

### T25 — Idempotent re-run + dedupe
**Priority:** SHOULD · **Depends on:** T24 · **Phase:** 🟨

**Task:** Ensure re-running the billing prompt doesn't double-chase: Notion query filters on
`Run ID`/invoice for dedupe (E10/X3) and Swytchcode idempotency key covers PayPal/Jira writes.

**Acceptance criteria:**
- [ ] Two consecutive identical prompts → one PayPal invoice, one Jira issue, no duplicate rows
- [ ] Behavior documented in README troubleshooting

---

## Phase 3 — UI, docs, demo, submission

### T31 — FastAPI + SSE server
**Priority:** MUST · **Depends on:** T17 · **Phase:** 🟩

**Task:** Implement `server/main.py`: `POST /run` (body `{prompt}`) starts a graph run and
returns a run id; `GET /stream/{run_id}` SSE endpoint emitting every trace event, approval
requests, and `done` with `final_answer`; `GET /healthz` reporting toolkit status; static-mount
`ui/`; bind `127.0.0.1` (SECURITY §1); serialize errors per E1/E9.

**Acceptance criteria:**
- [ ] `curl -N /stream/...` shows events arriving live during a run
- [ ] Empty prompt → 400 + readable message, no LLM call
- [ ] Server restart mid-run leaves UI in the E9 disconnected state, not a blank page

---

### T32 — Single-page trace UI
**Priority:** MUST · **Depends on:** T31 · **Phase:** 🟩

**Task:** Build `ui/index.html` strictly to `FRONTEND_SPEC.md` §§2–5: header + status pill,
prompt box with 3 demo chips, streaming timeline with trace cards (reasoning, canonical ID,
collapsible redacted JSON, decision footer, status pills), approval card (Approve/Deny +
120s timeout UI), final answer block, toasts, disconnected banner, mobile ≤640px behavior,
keyboard focus rules.

**Acceptance criteria:**
- [ ] Every component in the spec exists with the specified tokens (colors/spacing/type)
- [ ] A full run renders ≥7 cards live without manual refresh
- [ ] Approve button appears exactly when `approval_pending` arrives
- [ ] Opened at 375px width: usable, no horizontal scroll

---

### T33 — Failure drills
**Priority:** MUST · **Depends on:** T32, T24 · **Phase:** 🟪

**Task:** Scripted rehearsal of SECURITY §4/§5: kill Wi-Fi mid-run (E9), unset Gemini key (E2),
disable Gmail (E3), deny approval (E6), re-run same prompt (E10), paste foreign prompt (X11).
For each, verify the documented user-facing behavior appears.

**Acceptance criteria:**
- [ ] All 6 drills pass; any mismatch fixed or doc updated
- [ ] Backup video recorded after drills pass (`docs/demo/run.mp4`, gitignored)

---

### T34 — README (submission artifact)
**Priority:** MUST · **Depends on:** T24 · **Phase:** 🟪

**Task:** Write root `README.md`: what LedgerPilot is + GIF/screenshot of the trace, agent flow
diagram, **evidence block** (`tooling.json` excerpt listing 5 toolkits + canonical IDs), setup
instructions (prereqs → `./scripts/setup.sh` → auth → `.env` → `python -m server.main`), the 3
demo prompts, architecture link, troubleshooting, event/track attribution (Build with Swytchcode
× KNOTiC), license.

**Acceptance criteria:**
- [ ] A stranger can go clone → run → see a demo using only README
- [ ] ≥3 Swytchcode integrations explicitly visible with canonical IDs
- [ ] Architecture diagram renders (Mermaid)

---

### T35 — Architecture diagram doc
**Priority:** MUST · **Depends on:** T17 · **Phase:** 🟪

**Task:** Keep `docs/TECHNICAL_ARCHITECTURE.md` §2 Mermaid diagram in sync with the built graph
(current node set, conditional edges, approval gate, 5 toolkits). Render check on GitHub.

**Acceptance criteria:**
- [ ] Diagram matches the code as-built
- [ ] Renders on GitHub mobile

---

### T36 — Public GitHub repo + final push
**Priority:** MUST · **Depends on:** T34 · **Phase:** 🟪

**Task:** Create public repo, `.gitignore` audit (T01 grep), push all source + docs, verify from
a fresh clone. Repo name suggestion: `ledgerpilot-swytchcode`.

**Acceptance criteria:**
- [ ] Public URL loads with README rendered
- [ ] Zero secrets in git history
- [ ] Fresh clone runs under 10 minutes to first demo

---

### T37 — Commudle submission
**Priority:** MUST (deadline 15:30) · **Depends on:** T36 · **Phase:** 🟪

**Task:** Submit at `https://www.commudle.com/builds/create?campaign=BuildWithSwytchcode` with
repo URL, description, screenshots/video; target completion by **15:15**. Then tick
`SUBMISSION_CHECKLIST.md`.

**Acceptance criteria:**
- [ ] Submission confirmation visible before 15:30
- [ ] All checklist items in Doc 6 checked

---

### T38 — Optional social post
**Priority:** NICE · **Depends on:** T36 · **Phase:** 🟪

**Task:** LinkedIn/X post with a trace screenshot mentioning @Swytchcode and the event.

**Acceptance criteria:**
- [ ] Post live with repo link before closing ceremony

---

## Priority summary

| Priority | Tickets |
|---|---|
| **MUST** (demo floor) | T01, T02, T11–T18, T21, T22, T24(paypal+slack+notion), T31, T32, T33, T34, T35, T36, T37 |
| **SHOULD** | T23 (live Gmail), T24 (Jira), T25 |
| **NICE** | T38, deploy/public URL, extra toolkits |

**Cut-line rule:** if time collapses on-site, ship the MUST set —
PayPal + Slack + Notion alone satisfy the ≥3 requirement; Gmail/Jira degrade gracefully by design.
