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
swy auth connect gmail               # then: slack, notion, jira (paypal connect = broken upstream, skip)
swy auth status                      # expect 4 connected (gmail slack notion jira)
python scripts/smoke_test.py         # GATE B: ≥3 PASS (target 4–5) — record the matrix
python scripts/verify_canonical_ids.sh   # all 7 IDs PASS → otherwise fix IDs (note below)
python -m pytest tests/ -q           # 19 green
python scripts/ui_demo.py            # 17 UI checks + fresh screenshots/video
MOCK_LLM=1 python -m server.main     # sanity UI at http://localhost:8000
```

**ID mismatches:** if `verify_canonical_ids.sh` fails, find the real ID with
`swy search <toolkit>` or `swy discover "<intent>"`, then edit `.swytchcode/tooling.json`
and `docs/FRONTEND_SPEC.md §6` (they are the same source of truth). Canonical IDs in the
spec are marked *illustrative* until this step passes.

**Auth gotchas (all verified live 2026-09-26):**
- **Jira:** the Atlassian screen shows *"Access denied — requires access to a Jira site…"*
  if your account has **no Jira site**. Create a free one first (`id.atlassian.com` →
  Jira → pick a domain), then `swy auth connect jira`.
- **Jira base URL:** after connect, `.swytchcode/integrations/manifest.json` → `Jira.jira@v1`
  must use `https://api.atlassian.com/ex/jira/<cloudId>` (NOT `your-domain.atlassian.net`).
  Get cloudId: `https://<your-site>.atlassian.net/_edge/tenant_info` → or post-connect,
  call `https://api.atlassian.com/oauth/token/accessible-resources` with the credential
  from the connect flow. **Do not re-run `swy get jira` after editing — it overwrites back.**
  Verify with `swy exec jira.api.myself.list --json` (add via `swy add method` first).
- **PayPal connect** fails upstream (`invalid client_ID or redirect_uri` — Swytchcode's
  PayPal OAuth app), and the invoicing bundle injects **no auth**, so live PayPal calls
  return **401**. Known-blocked: smoke shows an honest PayPal FAIL; the agent degrades
  to a visible trace error (E5). Mock mode still demos the full PayPal flow.
- **`swy exec` exits 0 on HTTP 4xx/5xx** (payload carries `status_code`/`error_category`
  instead). `agent/swx.py` now detects API errors + unwraps the `{"data": …}` envelope —
  never trust exit codes alone when writing new checks.
- **Slack scopes are minimal** (`channels:read, im:read, users:read, chat:write, im:write`):
  the bot canNOT create/join channels. Create the public channel yourself, then
  `/invite @swytchcode` inside it — post is `not_in_channel` until invited.
- **Notion quirks hit in build:** bundle has no database-create method → create via raw
  `POST /v1/databases` (token from `.../connected-accounts/notion/credential-package`), add
  columns with `notion.data_source.update`; page rows need **typed** property values
  (`{"rich_text":[{"text":{"content":…}}]}` — plain strings → 400). Fetching credential-package
  **rotates** the token and breaks the CLI cache (401): fix with
  `sqlite3 ~/.swytchcode/credentials.db "update credential_cache set expires_at=1 where provider_slug='notion'"`,
  next exec auto-refreshes.
- **Jira `issue.create` needs ADF** description (`{"type":"doc","version":1,…}`) — plain text →
  400 "not valid Atlassian Document Format". Node handles this (`_adf`).
- **Headless/SSH boxes:** `swy auth connect` prints no URL (browser-open fails silently).
  Workaround that works: run a local pass-through proxy on `:8787` to
  `api-v2.swytchcode.com`, launch `SWYTCHCODE_API_URL=http://127.0.0.1:8787 swy auth connect <p>`
  in background, read `authorization_url` from the proxy log, paste it to the user's browser.

**Env knobs (all in `.env`, gitignored):**

| Var | Purpose | This build |
|---|---|---|
| `LLM_PROVIDER` | gemini (default) or groq first — gemini free tier = **20 req/day** | `groq` |
| `JIRA_PROJECT_KEY` / `JIRA_ISSUE_TYPE` | escalate target (code default `OPS`/`Bug`) | `SCRUM` / `Task` |
| `SLACK_CHANNEL` | summary channel (code default `#finance-ops`) | `#finance-ops` |
| `NOTION_DATA_SOURCE_ID` / `NOTION_DATABASE_ID` | data-source uuid (queries) + database uuid (row parent) | **both set** in `.env` |

**Dashboard chores (accounts — 30 min):**

| Service | Do |
|---|---|
| Google Cloud | enable Gmail API · OAuth consent = Testing · add your account as test user |
| Gmail | send 4 self-addressed emails matching `seed/invoices.json` (Acme/Northwind/Bluebird/Cobalt) |
| Notion | **DONE** — DB **LedgerPilot Ops Log** created via API (`POST /v1/databases` + `notion.data_source.update`, 11 columns incl. `Name`); ids in `.env`. Manual fallback: create DB, share with integration **Swytchcode**, put UUID in `.env` |
| Slack | **public** `#finance-ops` → `/invite @swytchcode` (bot cannot self-join: no `channels:join`) |
| Jira | free Cloud site `mohitdwivedi633.atlassian.net` · `.env` = `JIRA_PROJECT_KEY=SCRUM`, `JIRA_ISSUE_TYPE=Task` (site has no OPS/Bug) · manifest base URL already fixed (see auth gotchas) |
| PayPal | sandbox endpoint already live for invoicing (`api-m.sandbox.paypal.com`) — connect is optional/broken upstream |

---

## EVENT DAY — venue (see `BUILD.md` for full timeboxes)

**Bring-up (Block 1):**
```bash
git pull && source .venv/bin/activate
./scripts/setup.sh && swy auth status
./scripts/auth_connect_all.sh        # YOUR terminal: browser opens per provider (skip paypal/jira if blocked — see auth gotchas)
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
