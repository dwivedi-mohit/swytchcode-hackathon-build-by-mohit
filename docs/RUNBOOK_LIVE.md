# LIVE RUNBOOK — tonight + event day + Commudle draft

**Product:** LedgerPilot · Track 6 · Solo
**Purpose:** copy-paste one-sheet for everything that must happen **outside this sandbox**
(Swytchcode registry & third-party services are unreachable from it — verified).
**Companion:** `BUILD.md` (timeboxed plan) · `SUBMISSION_CHECKLIST.md` (tick-list).

---

## TONIGHT — your laptop (≈60–90 min, BUILD.md Phase 0)

```bash
git clone https://github.com/dwivedi-mohit/swytchcode-hackathon-build-by-mohit.git
cd swytchcode-hackathon-build-by-mohit

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm install -g swytchcode            # if permission denied:
                                     #   npm config set prefix ~/.local && npm install -g swytchcode
                                     #   export PATH="$HOME/.local/bin:$PATH"

cp .env.example .env                 # paste your GEMINI_API_KEY / GROQ_API_KEY
./scripts/setup.sh                   # swy init → get 5 toolkits → add tools → policy validate → doctor
swy auth connect paypal              # repeat for: gmail, slack, jira, notion
swy auth status                      # expect 5 connected
python scripts/smoke_test.py         # GATE B: ≥3 PASS (target 5) — record the matrix
python scripts/verify_canonical_ids.sh   # all 7 IDs PASS → otherwise fix IDs (note below)
python -m pytest tests/ -q           # 19 green
python scripts/ui_demo.py            # 17 UI checks + fresh screenshots/video
MOCK_LLM=1 python -m server.main     # sanity UI at http://localhost:8000
```

**ID mismatches:** if `verify_canonical_ids.sh` fails, find the real ID with
`swy search <toolkit>` or `swy discover "<intent>"`, then edit `.swytchcode/tooling.json`
and `docs/FRONTEND_SPEC.md §6` (they are the same source of truth). Canonical IDs in the
spec are marked *illustrative* until this step passes.

**Dashboard chores (accounts — 30 min):**

| Service | Do |
|---|---|
| Google Cloud | enable Gmail API · OAuth consent = Testing · add your account as test user |
| Gmail | send 4 self-addressed emails matching `seed/invoices.json` (Acme/Northwind/Bluebird/Cobalt) |
| Notion | create DB **LedgerPilot Ops Log** with the 10 columns in `TECHNICAL_ARCHITECTURE §4.2` · Share → your integration |
| Slack | private `#finance-ops` · invite the Swytchcode Slack bot/app |
| Jira | free Cloud site · project key **OPS** · API token via `swy auth connect jira` |
| PayPal | **sandbox** business + personal test accounts (Settings → API credentials) |

---

## EVENT DAY — venue (see `BUILD.md` for full timeboxes)

**Bring-up (Block 1):**
```bash
git pull && source .venv/bin/activate
./scripts/setup.sh && swy auth status
./scripts/auth_connect_all.sh        # YOUR terminal: browser opens per provider (gmail→slack→notion→jira→paypal)
python scripts/smoke_test.py            # Gate B: ≥3 PASS on venue wifi
./scripts/verify_canonical_ids.sh       # Gate B IDs: 7/7 PASS
# Kernel-policy demo (30s, judge-facing) — both commands print the guard firing:
printf '{"tool":"invoices.invoicing.send.create","args":{"invoice_id":"INV-1"}}' \
  | swy exec --dry-run --json ; echo "exit=$?"      # EXPECT exit 7: approval policy paypal-approval
printf '{"tool":"invoices.invoicing.invoices.create","args":{"env":"live"}}' \
  | swy exec --dry-run --json ; echo "exit=$?"      # EXPECT exit 6: blocked by paypal-sandbox-only
swy audit policy                              # violation history for judges
# if wifi dies → demo continues in mock: MOCK_LLM=1 MOCK_SWX=1 python -m server.main
```

**First live run (Block 4) — Gate E:**
```bash
python -m server.main                   # .env loaded → live LLM; swy auth present → live tools
# open http://localhost:8000 → Billing-day prompt → Run → Approve
# EXPECT: real PayPal sandbox invoice id, real Slack ts, real Notion page_id, real Jira key
```
Watch for: kernel policy `REQUIRES_APPROVAL` will hold the PayPal exec (`swy policy list` →
`paypal-approval`, fires on `invoice_id exists`). That's the policy working — approve in the UI,
and if the kernel still holds the call non-interactively, show judges
`printf '{"tool":"invoices.invoicing.send.create","args":{"invoice_id":"INV-1"}}' | swy exec --dry-run --json`
(exit 7: "matches an approval policy") plus the UI approval card (belt **and** suspenders is the story).

**Quick fixes:**

| Symptom | Command |
|---|---|
| LLM quota/keys missing | `.env` → `MOCK_LLM=1` (UI still streams; pill shows mock) |
| Toolkit auth expired | `swy auth status` → `swy auth connect <provider>` |
| Provider bundle missing | `./scripts/setup.sh` |
| Everything down | `MOCK_LLM=1 MOCK_SWX=1 python -m server.main` + backup video `docs/demo/run.mp4` |

---

## COMMUDLE DRAFT — paste-ready fields
*`https://www.commudle.com/builds/create?campaign=BuildWithSwytchcode` · target ≤15:15 · hard 15:30*

| Field | Value |
|---|---|
| **Project name** | LedgerPilot — AI Revenue Operations Agent |
| **Repository** | `https://github.com/dwivedi-mohit/swytchcode-hackathon-build-by-mohit` |
| **Track** | Track 6 (PayPal, Gmail, Slack, Jira, Notion) · **Solo** |
| **Tech stack** | Python · LangGraph · FastAPI + SSE · Swytchcode Runtime (5 toolkits) · single-file UI |
| **One-line pitch** | An agent that runs billing day for you — reads invoice emails, chases overdue payments through PayPal behind a human-approval gate, escalates disputes to Jira, logs to Notion, and summarizes in Slack — with a live audit trace of every call. |

**Description (≈150 words):**

> LedgerPilot automates SMB "billing day": one prompt turns into a LangGraph plan — intake,
> classify, act, report. It reads invoice emails (Gmail), labels them with an LLM, then takes
> conditional action: overdue → PayPal payment chase, disputed → Jira escalation (PayPal is
> deliberately skipped), everything → a Notion ops log whose Status column copies the *actual*
> API responses, and a Slack summary composed from real results. Every step streams to a dark
> trace UI as it happens — reasoning, Swytchcode canonical ID, request/response, decision.
> Safety is structural: `policies.json` (kernel-enforced `REQUIRES_APPROVAL` + UI Approve
> button) means the AI cannot move money alone; Gmail is policy-blocked from writing; PayPal
> is sandbox-pinned. Failures degrade honestly — missing Gmail falls back to seed data with a
> "DEMO DATA" pill, provider outages become visible trace cards. Built solo with LangGraph +
> Swytchcode across all five Track 6 toolkits, 19 automated tests, and a 17-check browser E2E.

**Attach:**
- `docs/screenshots/04-approval.png` (approval gate) and `docs/screenshots/05-final.png` (full trace)
- `docs/demo/run.mp4` (30–60 s demo video — re-record with `python scripts/ui_demo.py` after Gate E)
- Architecture diagram renders from README Mermaid (verify on GitHub mobile)

**Also don't forget:** track selection form `https://forms.gle/DZz8fzQh8PNxcbPXA`
(irreversible — **Track 6**).

---

*Post-submit: re-walk `SUBMISSION_CHECKLIST.md` §6–7, keep server runnable for Q&A.*
