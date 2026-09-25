# Build Playbook — How This Gets Built

**Product:** LedgerPilot — AI Revenue Operations Agent
**Version:** v1.0 · **Date:** 25 September 2026
**Companion docs:** `TICKETS.md` (work items) is *what* to build — this doc is *when and in
what order*, with the exact commands, gates, and cut-lines.

---

## 0. How the docs fit together

| Doc | Answers |
|---|---|
| `PRD.md` | What are we building and why |
| `TECHNICAL_ARCHITECTURE.md` | What are the pieces and how do they connect |
| `SECURITY.md` | Who may do what; what happens when things break |
| `FRONTEND_SPEC.md` | How it looks + the exact API/integration calls |
| `TICKETS.md` | The work items (T01…T38) |
| **`BUILD.md` (this file)** | **Chronological execution plan with timeboxes and gates** |
| `SUBMISSION_CHECKLIST.md` | Proof of done before 15:30 |
| `DEMO_SCRIPT.md` | The 2.5-minute pitch |

**Single source of truth for scope:** PRD. **Single source of truth for order:** this file.

---

## 1. Phase 0 — Tonight (prep day, ~2–3 h at home)

Goal: *zero unknowns about the platform* before venue wifi and a countdown clock exist.

| # | Task | Ticket | Command / output |
|---|---|---|---|
| 0.1 | Create repo skeleton + docs committed | T11 (partial) | `git init`, push docs/ |
| 0.2 | Swytchcode init + toolkits | T01 | `./scripts/setup.sh` → `.swytchcode/tooling.json` lists 5 toolkits |
| 0.3 | Smoke test the 5 toolkits from home wifi | T02 | `python scripts/smoke_test.py` → target 5 PASS, floor 3 |
| 0.4 | LLM keys verified | T13 | Gemini + Groq both return a completion; `MOCK_LLM=1` works offline |
| 0.5 | Full mock E2E green | T11–T18 | `pytest` green, <10 s, no keys |
| 0.6 | Gmail OAuth plumbing done at home | T23 | API enabled, consent in Testing mode, 4 test-user emails queued |
| 0.7 | Notion Ops DB created + shared to integration | T24 | DB exists with the 10 properties from TECHNICAL_ARCHITECTURE §4.2 |
| 0.8 | Slack private `#finance-ops` + bot invited | T24 | bot in channel, `chat.postMessage` smoke PASS |
| 0.9 | Jira site + `OPS` project + API token | T24 | issue creatable via smoke test |
| 0.10 | PayPal sandbox accounts ready | T24 | sandbox business + personal test accounts exist |
| 0.11 | Record backup demo video | T33 | `docs/demo/run.mp4` exists (gitignored) |

**Gate A (leave-home check):** `pytest` green + `smoke_test.py` ≥3 PASS + repo public-able with
no secrets. If Gate A fails → fix tonight, not tomorrow.

**Tonight's rule:** if something needs a *dashboard click* (GCP console, Notion share, Jira
project, PayPal sandbox), do it now — those are the things that eat venue hours.

---

## 2. Phase 1 — On-site build morning (09:00 → 13:25, ≈4 h 25 m)

Assume 09:00 start, 15:30 submission deadline → build window 09:00–13:25, buffer 13:25–15:30
for demo rehearsals, docs, and Commudle upload.

Work in **fixed timeboxes**. Each block ends with a **gate** — do not proceed on a red gate.

### Block 1 — 09:00–09:20 · Platform bring-up (20 min)
- [ ] Clone repo, `./scripts/setup.sh`, `swy doctor` clean (T01)
- [ ] Venue wifi confirmed working for Swytchcode + Gemini + Groq
- [ ] `python scripts/smoke_test.py` → record PASS matrix here:

  | toolkit | result | ms |
  |---|---|---|
  | gmail | ___ | ___ |
  | paypal | ___ | ___ |
  | jira | ___ | ___ |
  | notion | ___ | ___ |
  | slack | ___ | ___ |

- [ ] Backup: hotspot phone tested with one Swytchcode call

**Gate B:** ≥3 toolkits PASS on venue wifi (PayPal, Slack, Notion minimum).
**If red:** still proceed — mock mode (T13/T18) keeps the demo alive; re-run smoke in Block 4.

### Block 2 — 09:20–10:30 · Core agent, mock end-to-end (70 min)
- [ ] State + redaction (T12)
- [ ] LLM switch gemini|groq|mock (T13)
- [ ] Seed intake (T14)
- [ ] plan + classify (T15)
- [ ] Five action nodes against mocked `swx.execute` (T16)
- [ ] Graph assembly + conditional edges (T17)
- [ ] `pytest` green (T18)

**Gate C:** `pytest` green — full billing-day run under `MOCK_LLM=1` produces ≥6 trace events,
disputed invoice has zero PayPal calls, read-only prompt writes nothing.

### Block 3 — 10:30–11:30 · Server + UI (60 min)
- [ ] FastAPI + SSE (T31)
- [ ] Single-page trace UI per FRONTEND_SPEC (T32)
- [ ] Approval card round-trip wired to state flag (T32/T22 client side)

**Gate D:** `python -m server.main` → open `http://localhost:8000` → mock run streams cards
live, approval card appears and Approve/Deny works against the mock.
**This is the first "judge-ready screenshot" moment — take it.**

### Block 4 — 11:30–12:30 · Live integrations (60 min)
Order chosen so **the 3 most valuable land first** (PayPal → Slack → Notion), then Jira, Gmail:
- [ ] `swy login` / `swy auth` each toolkit (T24)
- [ ] Swytchcode wrapper + idempotency + redaction (T21)
- [ ] **PayPal live** behind approval gate + `policies.json` (T22, T24)
- [ ] **Slack live** summary post (T24)
- [ ] **Notion live** row writes (T24)
- [ ] Jira live (T24/SHOULD)
- [ ] Gmail live intake (T23/SHOULD) — else stays on seed with honest pill

**Gate E:** one complete live run: real PayPal ID + Slack `ts` + Notion `page_id`
(+ Jira key, Gmail live if lucky). Update FRONTEND_SPEC §6 canonical IDs from "illustrative"
to confirmed.

**Cut-line:** if 12:30 hits with only 2 of 5 live → freeze scope, do NOT start T25; go to Block 5.

### Block 5 — 12:30–13:25 · Hardening + demo prep (55 min)
- [ ] Failure drills: E2 (no Gemini key), E3 (Gmail off), E6 (deny approval), E10 (re-run),
      X11 (foreign prompt), E9 (wifi drop) — T33
- [ ] Re-record backup video if behavior changed — T33
- [ ] One full demo dry run with timer (target ≤3 min) — see `DEMO_SCRIPT.md`
- [ ] Sync architecture Mermaid diagram to as-built — T35

**Gate F:** drills pass + demo runs ≤3 min without crash.

**13:25 hard stop on coding.** Buffer block below.

---

## 3. Phase 2 — Submission window (13:25 → 15:30, ≈2 h)

| Time | Task | Ticket |
|---|---|---|
| 13:25–13:55 | README: hero screenshot, evidence block (`tooling.json` excerpt), setup steps, 3 prompts, diagram | T34 |
| 13:55–14:15 | Final `git` audit: no secrets in history, `.gitignore` covers `.env`/auth/mp4 | T36 |
| 14:15–14:35 | Push public repo; verify fresh-clone instructions in a temp dir | T36 |
| 14:35–14:50 | Screenshots (trace with approval card, live run results) + optional short video | — |
| 14:50–15:10 | **Commudle submission** — `https://www.commudle.com/builds/create?campaign=BuildWithSwytchcode` | T37 |
| 15:10–15:20 | Walk `SUBMISSION_CHECKLIST.md` tick every box | Doc 6 |
| 15:20–15:30 | Buffer / fix / breathe | — |

**Gate G:** submission confirmation received **before 15:30** (target ≤15:15).

**Rule:** nothing new gets built after 13:25 except fixes required to make Gate G pass.

---

## 4. Standing rules during the build

1. **Mock first, live second.** Every layer must run under `MOCK_LLM=1` + fake `swx.execute`
   before a real credential touches it. Keeps Gates C/D green even if venue wifi dies.
2. **Trace is the product.** A feature isn't done until it renders as a card with toolkit,
   canonical ID, reasoning, decision. Judges score the API integration (30%) — invisible calls
   score zero.
3. **Never widen scope.** PRD §8 (out of scope) is law. New idea → write it in a `nice-to-have`
   note, don't build it.
4. **Fail loud, degrade gracefully.** Every error path in SECURITY §4 must show as a card/banner
   — never a stack trace on the projector.
5. **Commit at every green gate** (C, D, E, F): `git commit -m "gate <x>: <what works>"`.
   Frequent commits = easy rollback + visible history in the repo.
6. **One runner.** One person executes this plan; others write docs/README/screenshots from the
   companion docs rather than editing code mid-flight.

---

## 5. Cut-lines (decide *now* what dies later)

| Pressure | Cut | Keep |
|---|---|---|
| Block 4 runs long | Gmail live (seed pill stays), Jira live (Notion row only) | PayPal + Slack + Notion = 3-toolkit floor |
| Block 2 runs long | read_only prompt polish, dedupe (T25) | Gates C+D non-negotiable |
| Block 3 runs long | chips, toasts, mobile polish | streaming cards + approval card |
| Before 14:00 anything broken | backup video + seed-everything | repo must be public with README |

**Kill switch (worst case):** everything live fails → ship mock-mode demo + backup video;
README states integrations verified pre-event. Mock E2E still demonstrates all 5 toolkits'
wiring; never submit an empty repo.

---

## 6. Definition of Done (one screen)

```
[ ] Gate A: home prep green (pytest + ≥3 toolkit smoke)
[ ] Gate B: venue smoke ≥3 PASS (or mock-mode fallback confirmed)
[ ] Gate C: pytest green, mock E2E full run
[ ] Gate D: localhost:8000 streams cards, approval round-trip works
[ ] Gate E: one live run with real PayPal/Slack/Notion IDs
[ ] Gate F: failure drills pass, demo ≤3 min
[ ] Gate G: Commudle submission confirmed ≤15:30
```

---

*Next: read `TICKETS.md` for the itemized prompts, `DEMO_SCRIPT.md` for the pitch.*
