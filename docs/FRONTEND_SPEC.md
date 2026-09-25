# Frontend Specification Document

**Product:** LedgerPilot — AI Revenue Operations Agent
**Version:** v1.0 · **Date:** 25 September 2026
**Scope:** design system for the single-page trace UI (`ui/index.html`) + the complete API &
integration spec for all five Swytchcode toolkits.

---

## 1. Design Intent

A **dark, terminal-inspired operator console**. The UI's job is to make the agent's reasoning and
Swytchcode calls legible on a projector in ≤2.5 minutes — not to win a beauty contest (UX is 5%
of the rubric). One screen, one column, no navigation.

Archetype: developer-tool / observability dashboard. Think "incident timeline", not "marketing
site."

---

## 2. Color Palette

| Token | Hex | Usage |
|---|---|---|
| `--bg` | `#0B0E14` | page background |
| `--surface` | `#141824` | cards, prompt box, header |
| `--surface-2` | `#1C2130` | nested blocks (request/response JSON), hover |
| `--border` | `#2A3142` | 1px borders, dividers |
| `--text` | `#E6E9F0` | primary text |
| `--text-dim` | `#8B93A7` | timestamps, labels, secondary text |
| `--primary` | `#4F8CFF` | Run button, focus rings, links, active step |
| `--primary-hover` | `#3D78E6` | Run button hover |
| `--success` | `#2FBF71` | status pills: ok, APPROVED, toolkit connected |
| `--warning` | `#E8A33D` | amber cards: pending approval, failover, fallback labels |
| `--error` | `#E05252` | failed calls, validation errors, DENY |
| `--accent` | `#9B6DFF` | brand accent: logo mark, step numbers |
| `--code-key` | `#7EC3FF` | JSON keys |
| `--code-str` | `#A8D97A` | JSON string values |

**Contrast rule:** all text ≥ 4.5:1 against its background. Status is **never color-only** — every
pill carries text (and optional icon glyph), for color-blind safety and projector washout.

---

## 3. Typography

| Role | Font | Size / weight | Notes |
|---|---|---|---|
| UI / body | `Inter, ui-sans-serif, system-ui, sans-serif` | 14px / 400, line-height 1.5 | system stack — no font downloads |
| Header title | same | 18px / 600 | "LedgerPilot" + version |
| Card title (node name) | same | 13px / 600, uppercase, letter-spacing 0.06em | e.g. `PAYPAL_CHASE` |
| Reasoning text | same | 14px / 400 italic | agent's stated reasoning |
| Labels (toolkit, canonical ID) | `ui-monospace, SFMono-Regular, Menlo, monospace` | 12px / 500 | monospace = machine data |
| JSON blocks | monospace | 12px / 400, line-height 1.45 | pre-wrap, max-height 220px, scroll |
| Final answer | same | 15px / 400, line-height 1.6 | largest body text — it's the payoff |
| Buttons | same | 14px / 600 | sentence case: "Run", "Approve", "Deny" |

Rules: max 3 sizes visible at once; no centered paragraphs; tabular numerals for amounts.

---

## 4. Component Styles

### 4.1 Header (sticky, height 56px)
`--surface` bg, 1px bottom `--border`. Left: accent square (24px, `--accent`) + "LedgerPilot" +
dim subtitle "AI Revenue Ops · Swytchcode × LangGraph". Right: **connection pill** —
"● 5 toolkits connected" (`--success`) or "● degraded: seed intake" (`--warning`).

### 4.2 Prompt box (fixed under header)
- Container: `--surface`, 1px `--border`, radius 10px, padding 16px, max-width 900px, centered
- `<textarea>`: transparent bg, `--text`, 15px, min-height 72px, auto-grow to 160px, no resize
- Placeholder: *"It's billing day. Find unpaid invoices, chase overdue ones with PayPal,
  escalate disputes to Jira, log to Notion, summarize in Slack…"*
- Footer row inside container: left = hint chips (3 clickable demo prompts), right = **Run button**
- **Run button:** `--primary` bg, white text, radius 8px, padding 10px 22px, hover
  `--primary-hover`; disabled state: opacity .5, cursor not-allowed, label "Running…"
- Validation error (E1): message under box in `--error`, 13px; border pulses `--error` once

**Demo prompt chips** (click = fill textarea): `Billing day (full run)` · `Only > ₹50,000` ·
`What did we chase this week?` — chip style: `--surface-2`, 1px border, radius 999px, 12px text.

### 4.3 Trace timeline (main column)
Vertical feed, max-width 900px, 16px gap between cards, left rail 2px `--border` connecting
step dots (10px circles, `--accent` fill when done, pulsing when active).

### 4.4 Trace card (the core component)
- `--surface`, 1px `--border`, radius 10px, padding 14px 16px
- **Header row:** step dot number (accent) · node name (uppercase mono) · toolkit pill ·
  status pill · timestamp (`--text-dim`, 12px, right)
- **Reasoning body:** italic 14px paragraph
- **Canonical ID line:** mono chip `swy exec paypal.invoices.send` on `--surface-2`
- **Collapsible JSON** (`▸ request` / `▸ response`): `<details>` styled, mono 12px, syntax-tinted
  keys/values; `Authorization` rendered as `"***"`
- **Decision footer:** 1px top border, prefix `→ decision:` in `--accent`, then text
- **Status pills:** `ok` (success) · `pending_approval` (warning, pulsing) · `approved`
  (success) · `failed` (error) · `skipped` (dim) · `seed` (warning, label "DEMO DATA")
- Cards enter with 180ms fade+slide-up; no other motion

### 4.5 Approval card (PayPal gate) — differs from normal card
- Border: 1px `--warning`; top strip 3px `--warning`
- Body shows the **exact** PayPal request JSON (amount, vendor, invoice id)
- Buttons row: **Approve** (`--success` bg, white) · **Deny** (`--error` bg, white)
- Caption (dim 12px): "Required by policy `policies.json` · approval binds to this request"
- After click: buttons replaced by pill `approved by operator` / `denied by operator` + timestamp
- Auto-timeout at 120s → card turns dim, pill `timed out` (SECURITY E7)

### 4.6 Status / toast messages
- Top-right toasts, `--surface-2`, 1px border, radius 8px, auto-dismiss 5s
- Types: success (green left-border), warning (amber), error (red, sticky until dismissed)

### 4.7 Final answer block
- `--surface`, 1px `--success` left-border 3px, radius 10px, padding 18px 20px
- Heading "Result" (13px uppercase dim) + body 15px
- Inline mono chips for IDs (PayPal `INV-…`, Jira `OPS-…`)
- Footer row: **Run again** (ghost button) · **Copy summary** · link "open backup video"

### 4.8 Empty & loading states
- Empty: centered dim text "Run a prompt to watch the agent work" + tiny glyph
- Loading: active step dot pulses; Run disabled; skeleton shimmer inside the newest card
- Disconnected (E9): amber banner under header: "Connection lost — retry or use hotspot" +
  **Retry** button

---

## 5. Spacing & Layout Rules

- **Grid:** single column, `max-width: 900px`, centered, 24px side padding
- **Spacing scale:** 4 / 8 / 12 / 16 / 24 / 32 — only these values
- **Card padding:** 14px 16px · **card gap:** 16px · **section gap:** 24px
- **Radius:** cards/buttons/inputs 8–10px · pills 999px · JSON blocks 6px
- **Borders:** always 1px `--border`; emphasis uses a colored 3px left/top edge, never thick rings
- **Shadows:** none (flat design; depth via surface steps)
- **Breakpoints:** ≤640px — padding 12px, JSON collapses by default, buttons full-width,
  header subtitle hidden. The UI must be readable when a judge opens it **on a phone**
- **Focus:** 2px `--primary` outline, offset 2px — keyboard operable (Tab/Enter on Run, Approve)
- **Motion:** only card entrance (180ms) + pending-pill pulse; `prefers-reduced-motion` disables both

---

## 6. API & Integration Spec (the 30%-rubric section)

Every service below is called **exclusively through the Swytchcode Runtime SDK** —
`swx.tools.execute(<canonical_id>, {...})` — never raw HTTP. Canonical IDs are illustrative and
must be confirmed against `swy info <id>` during setup; `tooling.json` is the committed source
of truth.

### 6.0 Shared call envelope

```python
result = swx.tools.execute("<canonical_id>", {
    "params": {...},                       # tool-schema validated by Swytchcode
    "Authorization": "Bearer <from swy auth>",
    "Idempotency-Key": f"{run_id}:{invoice_id}"   # writes only
})
# → {"canonical_id":..., "status":..., "body": {...}}  (structured JSON, validated)
```

Failure contract: non-2xx or validation error raises `ToolError` → node catches →
`trace.status = "failed"` + `errors[]` (SECURITY E5/E8).

---

### 6.1 Gmail — intake (`toolkit: gmail`) · **read-only**

| Property | Value |
|---|---|
| Purpose | Find unpaid-invoice emails and parse them into `Invoice` objects |
| Called from | `agent/nodes/intake.py` |
| Mode | `GMAIL_ENABLED=1`; falls back to `seed/invoices.json` on auth error (E3) |
| Read/write | **Read only** — send/modify tools are never enabled |

| Step | Canonical ID (illustrative) | Request | Response used |
|---|---|---|---|
| Search | `gmail.messages.list` | `{"q": GMAIL_QUERY, "maxResults": MAX_INVOICES}` | message IDs |
| Fetch | `gmail.messages.get` | `{"id": msg_id, "format": "full"}` | subject, snippet, date → LLM parses to `Invoice[]` |

**Output drives next action:** `invoices[]` is the sole input to `classify` — no invoices →
E4 clean stop.

---

### 6.2 PayPal — payment chase (`toolkit: paypal`) · **gated write**

| Property | Value |
|---|---|
| Purpose | Create/send a payment chase for OVERDUE invoices (sandbox only) |
| Called from | `agent/nodes/paypal_chase.py` |
| Gating | UI approval **and** `policies.json` rule requiring approval for `paypal.*` |
| Environment | `PAYPAL_ENV=sandbox` — enforced at config load |

| Step | Canonical ID (illustrative) | Request | Response used |
|---|---|---|---|
| Create chase | `paypal.invoices.create` (or `.send`) | `{"invoice": {"number": id, "amount": {"value": amt, "currency": cur}, "recipient": vendor}}` | `id` (`INV-…`), `status` |

**Output drives next action:** response `id`/`status` → Notion `PayPal Invoice ID` + `Status=CHASED`
→ Slack summary line. Denied/failed → `Status=SKIPPED` and Slack says so (E6/E5).

---

### 6.3 Jira — dispute escalation (`toolkit: jira`) · **write**

| Property | Value |
|---|---|
| Purpose | Turn each DISPUTED invoice into a tracked issue; **PayPal is skipped for these** |
| Called from | `agent/nodes/jira_escalate.py` |

| Step | Canonical ID (illustrative) | Request | Response used |
|---|---|---|---|
| Create issue | `jira.issues.create` | `{"fields": {"project": {"key": "OPS"}, "summary": "Dispute: <vendor> #<id>", "issuetype": {"name": "Bug"}, "priority": {"name": "High" if amount>50000 else "Medium"}, "description": <email excerpt + decision reason>}}` | `key` (`OPS-…`) |

**Output drives next action:** `key` → Notion `Jira Key` → Slack "escalated to OPS-142"
→ final answer. Priority is derived from the *invoice data* (amount), demonstrating
reasoned parameter selection.

---

### 6.4 Notion — operations log (`toolkit: notion`) · **write**

| Property | Value |
|---|---|
| Purpose | System of record: one row per invoice outcome (schema: TECHNICAL_ARCHITECTURE §4.2) |
| Called from | `agent/nodes/notion_log.py` |

| Step | Canonical ID (illustrative) | Request | Response used |
|---|---|---|---|
| Query DB | `notion.databases.query` | `{"database_id": OPS_DB, "filter": {"Run ID": run_id}}` | dedupe check (E10/X3) |
| Create row | `notion.pages.create` | `{"parent": {"database_id": OPS_DB}, "properties": {Invoice ID, Vendor, Amount, Due Date, Label, Status, PayPal Invoice ID, Jira Key, Run ID, Ran At}}` | `page_id` |

**Output drives next action:** `page_id` recorded in `results.notion`; Slack summary includes
row count ("4 rows logged").

---

### 6.5 Slack — team summary (`toolkit: slack`) · **write**

| Property | Value |
|---|---|
| Purpose | Post the run summary to `#finance-ops`; message text is **generated from actual results** |
| Called from | `agent/nodes/slack_summary.py` |

| Step | Canonical ID (illustrative) | Request | Response used |
|---|---|---|---|
| Post | `slack.chat.postMessage` | `{"channel": "#finance-ops", "text": summary_from_results}` | `ts`, `channel` |

**Output drives next action:** final answer quotes the posted text + `ts` permalink; failure →
summary rendered inline (X9).

Example generated text (values come from real responses, not the plan):

```
📋 Billing day run 2026-09-26 · 4 invoices
• Chased 1 via PayPal → INV-8F2K (Acme Supplies ₹5,400)
• Escalated 1 dispute to Jira → OPS-142 (Northwind LLP ₹18,200)
• Logged 4 rows in Notion Ops Log
• 1 due soon, 1 already paid — no action
```

---

### 6.6 LLM provider (not a Swytchcode toolkit, but an integration)

| Provider | Env | Library | When used |
|---|---|---|---|
| Gemini | `GEMINI_API_KEY` | `langchain-google-genai` | default (`LLM_PROVIDER=gemini`) |
| Groq | `GROQ_API_KEY` | `langchain-groq` | failover on 429/error (E2/E12) |
| Mock | `MOCK_LLM=1` | rule-based stub | tests / offline (`tests/test_graph.py`) |

Used by: `plan` (intent + mode), `classify` (labels + reasons), `respond` (summary phrasing).

---

### 6.7 Integration summary table (judge-facing)

| # | Toolkit | R/W | Node(s) | Canonical IDs | Consumed by | Demonstrates |
|---|---|---|---|---|---|---|
| 1 | gmail | R | intake | messages.list, messages.get | classify | intake → reasoning |
| 2 | paypal | W (gated) | paypal_chase | invoices.create/send | notion, slack | approval policy + value action |
| 3 | jira | W | jira_escalate | issues.create | notion, slack | conditional branch (dispute) |
| 4 | notion | R/W | notion_log | databases.query, pages.create | slack, respond | record of truth |
| 5 | slack | W | slack_summary | chat.postMessage | respond | results → communication |
| — | **5 toolkits · ≥6 canonical IDs · every output feeds the next step** | | | | | **requirement: ≥3** ✅ |

---

*Companions: `TECHNICAL_ARCHITECTURE.md` (node contract), `SECURITY.md` (redaction, errors),
`DEMO_SCRIPT.md` (how this is narrated in 2.5 minutes).*
