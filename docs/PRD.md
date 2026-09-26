# Product Requirements Document (PRD)

**Product:** LedgerPilot — AI Revenue Operations Agent
**Track:** Track 6 — AI Business Operator Agent (Build with Swytchcode, Gurgaon Edition)
**Version:** v1.0 (Hackathon MVP)
**Date:** 25 September 2026
**Status:** Approved for build

---

## 1. Problem Statement

Small businesses and freelancers run billing day by hand. An invoice arrives by email, someone
checks whether it is overdue, opens PayPal to chase it, pastes a row into a spreadsheet, remembers
to file a dispute somewhere, and finally types a summary into Slack. Every step lives in a different
tool, every step is manual, and the steps depend on each other — what you find in the inbox decides
what you do in PayPal, what PayPal says decides what you write in the spreadsheet.

The result: invoices go unchased, cash that should arrive in days arrives in weeks, disputes are
missed because nobody re-reads the inbox, and the "system of record" is a spreadsheet nobody trusts.

Existing tools solve fragments (an invoicing app, a payment link, a task board) but nothing joins
them into one operation that takes a plain-English request and executes the whole workflow. That
join — understanding a request, reasoning about what to do, choosing tools, executing across
services, and letting each result steer the next action — is exactly what an AI agent is for.

**Why it matters:** for a 5–20 person company, chasing invoices is 3–5 hours per week of
high-concentration work that a single operator does badly when interrupted. Getting paid days
earlier is the difference between making payroll and not.

---

## 2. Target Users

**Primary persona: "Priya" — the operator-owner**

- **Age / role:** 28–45, founder, finance lead, or ops manager at a small business or agency
- **Tech comfort:** High. Lives in Gmail, Slack, Notion daily. Comfortable pasting a prompt.
  Does not write code and does not want to configure webhooks, zaps, or API keys.
- **What she wants:** One place to run "billing day" — a single request that chases what is due,
  escalates what is wrong, records everything, and tells the team what happened.
- **What frustrates her:**
  - Copy-pasting the same data between Gmail, PayPal, Notion, and Slack
  - Forgetting which invoices were already chased (duplicate reminders embarrass her)
  - Finding out about a customer dispute three weeks late
  - Tools that act without showing their work — she will not trust an agent that moves money
    silently

**Secondary persona: the jury/mentor (demo evaluator)**

- Technical, time-boxed to 2.5 minutes, wants to see *the agent deciding*, not a scripted button.

---

## 3. Product Vision

> **The operator you brief once and never follow up with.** LedgerPilot becomes a general-purpose
> business-operations agent that runs multi-tool workflows from a single sentence — starting with
> accounts-receivable, expanding to any of the 359 integrations in the Swytchcode directory
> (expenses, vendor onboarding, reporting) without changing its architecture.

North star for v1: *an evaluator types one sentence into a browser and watches a real PayPal
invoice, Jira issue, Notion row, and Slack message get created as the visible result of agent
reasoning — each one gated, logged, and explained.*

---

## 4. Core Features

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| F1 | Natural-language prompt interface | Operator types a billing-day request in plain English into a web UI | **Must-have** |
| F2 | Agent reasoning graph | LangGraph agent plans the workflow, picks tools at each step, and routes conditionally based on what each API returns | **Must-have** |
| F3 | Email invoice intake (Gmail) | Agent reads invoice emails from Gmail, extracts vendor, amount, due date, invoice number | **Must-have** |
| F3a | Seed-data fallback intake | If Gmail auth is unavailable, agent reads `seed/invoices.json` with identical behavior | **Must-have** (demo safety) |
| F4 | Invoice classification | LLM labels each invoice OVERDUE / DISPUTED / DUE_SOON / PAID and decides the action | **Must-have** |
| F5 | PayPal payment chase | Overdue invoices → create/send a payment chase through PayPal (sandbox) | **Must-have** (track identity) |
| F6 | Human approval gate | Every `invoices.*` write requires one-click approval in the UI, enforced by Swytchcode `policies.json` | **Must-have** |
| F7 | Jira dispute escalation | Disputed invoices → Jira issue with priority scaled by amount; **explicitly skips PayPal** | **Must-have** |
| F8 | Notion operations log | Every outcome written to an Ops DB; status field = value actually returned by PayPal/Jira | **Must-have** |
| F9 | Slack team summary | Summary posted to `#finance-ops`, text generated from actual API results | **Must-have** |
| F10 | Live trace timeline | UI streams each step: reasoning → toolkit → canonical ID → request/response → decision | **Must-have** (this is the demo) |
| F11 | Secondary demo prompts | "Only chase invoices over ₹50,000" (re-reasoning) and "What did we chase this week?" (read-only mode) | **Must-have** |
| F12 | LLM provider failover | Gemini primary, Groq fallback, `MOCK_LLM` mode for tests | Should-have |
| F13 | Read-only mode | Agent declines write tools when the request is purely informational | Should-have |
| F14 | Idempotent re-runs | Re-running the same prompt does not double-send chases (Swytchcode idempotency keys) | Should-have |
| F15 | Backup demo video | Pre-recorded full run in case venue network fails | **Must-have** (risk control) |
| F16 | Public deploy of the UI | Hosted URL as an alternative to localhost | Nice-to-have |
| F17 | Additional toolkits (Stripe, etc.) | Demonstrates directory breadth | Nice-to-have |

---

## 5. App Flow (step-by-step, v1)

**Entry:** operator runs `python -m server.main`, opens `http://localhost:8000`.

1. **Landing.** Single page loads: header (LedgerPilot + status pill "5 toolkits connected"),
   prompt input box with placeholder, empty trace area, and a footer legend.
2. **Prompt entry.** Operator types: *"It's billing day. Find this week's unpaid invoices in my
   inbox, chase the overdue ones with PayPal, escalate suspicious ones to Jira, log everything in
   Notion, and summarize for #finance-ops."* Presses **Run** (or Enter).
3. **Validation.** Empty/too-short prompt → inline error message, no call made (edge case E1).
4. **Plan step.** Trace card 1 appears: agent's restatement of the plan
   ("intake → classify → act → log → report").
5. **Intake step.** Trace card 2: Gmail query executes → 4 invoices found (or seed fallback,
   labeled honestly in the trace). Cards show toolkit `gmail`, canonical ID, request, response.
6. **Classify step.** Trace card 3: table of 4 invoices with labels (1 OVERDUE, 1 DISPUTED,
   1 DUE_SOON, 1 PAID) and the agent's stated decision per invoice.
7. **Branch A — PayPal.** For the OVERDUE invoice: trace card 4 shows proposed `invoices.*` call →
   **APPROVE button appears** (policy gate). Operator clicks Approve → card updates with live
   PayPal sandbox response (invoice ID, status SENT).
8. **Branch B — Jira.** For the DISPUTED invoice: trace card 5 shows Jira issue created
   (key + priority), with decision note "skipped PayPal — disputed, per policy."
9. **Log step.** Trace card 6: Notion rows created; Status column mirrors PayPal/Jira responses.
10. **Report step.** Trace card 7: Slack message posted to `#finance-ops`; message text displayed
    in the card, generated from actual results (PayPal invoice ID, Jira key).
11. **Final answer.** Summary block renders: what was chased, what was escalated, what was logged,
    links/IDs — plus a "Run again" affordance.
12. **Failure paths (defined, see SECURITY doc):** prompt rejected, no invoices found, Gmail
    unavailable → seed, LLM down → Groq, PayPal rejected → retry then abort branch with message,
    network lost → status pill turns amber and a retry banner appears.

**Read-only flow (F13):** prompt 3 skips steps 7–10, answers from Notion/Gmail data, and the
trace explicitly shows "write tools not selected for this request."

---

## 6. MVP Definition

**MVP = F1, F2, F3a, F4, F5, F6, F7, F8, F9, F10, F11, F15**, wired to
**PayPal + Slack + Notion as the guaranteed floor** (meets the ≥3 Swytchcode requirement on its
own), with **Gmail and Jira as full members of the graph** that degrade gracefully.

Definition of done for MVP: from a cold laptop on venue Wi-Fi, one typed sentence produces a
visible trace ending in a real sandbox PayPal invoice, a Jira issue, Notion rows, and a Slack
message — twice in a row — within 2 minutes per run.

---

## 7. Success Metrics

| Metric | Target | Why |
|---|---|---|
| E2E demo success rate | ≥ 2 consecutive clean runs on venue network | Functionality (10%) + jury trust |
| Swytchcode toolkits executed per demo run | 5 (floor: 3) | Integration depth (30%) |
| Distinct canonical tool calls | ≥ 6 | "Deep integration" evidence |
| Conditional branches exercised in demo | ≥ 2 (PayPal path, Jira path) | Proof of agency vs. workflow |
| Time from prompt to final answer | ≤ 120 s | Fits the 2.5-min pitch |
| Trace cards rendered with request+response | 100% of tool calls | Makes the 30% *visible* |
| Commudle submission time | ≤ 15:15 (deadline 15:30) | Late submissions may not be judged |
| Shortlisting | Top 7–10 finalists | Mentor scores collected live on the floor |
| Rubric coverage | All 6 criteria have a concrete artifact | See SUBMISSION_CHECKLIST |

---

## 8. Out of Scope (deliberately NOT building in v1)

- **Real money movement.** PayPal sandbox only; no live credentials in the repo, ever.
- **Multi-user accounts / login.** Single-operator local tool; no signup, no sessions, no RLS.
- **Scheduling / autonomous runs.** No cron, no background polling — the agent runs when briefed.
- **Production deploy / domains / SSL.** Localhost is the demo surface; public URL is optional.
- **A traditional database.** The Notion Ops DB is the record of truth for v1; no Postgres/SQLite.
- **Email sending from the agent.** Chases go through PayPal; the agent reads Gmail but does not
  compose or send email (keeps scope and permissions tight).
- **Undo/rollback of created records.** Idempotency prevents duplicates; deleting is manual.
- **Mobile app, PWA packaging, offline mode.**
- **Multi-currency logic and tax computation.** Amounts are taken as written in the invoice.

---

## 9. Risks & Mitigations (product-level)

| Risk | Impact | Mitigation |
|---|---|---|
| Gmail OAuth not ready tonight | Intake dead | F3a seed fallback — identical trace, labeled honestly |
| PayPal API scope surprise | Track identity lost | Tonight's smoke test; pivot node to alternate PayPal action, graph unchanged |
| Venue network failure | Demo impossible | Backup video (F15) + hotspot + `--dry-run` |
| Judge confuses agent with workflow | Loses 20% innovation | Branch demo (prompt 2) + approval gate shown live |

---

*Companion docs: `TECHNICAL_ARCHITECTURE.md` (how), `SECURITY.md` (what can break),
`FRONTEND_SPEC.md` (how it looks), `TICKETS.md` (build order), `DEMO_SCRIPT.md` (how it's
presented), `SUBMISSION_CHECKLIST.md` (what ships).*
