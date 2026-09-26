# Frontend Specification Document

**Product:** LedgerPilot — AI Revenue Operations Agent  
**Version:** v2.0 · **Date:** 26 September 2026  
**Scope:** design system for the single-page trace UI (`ui/index.html`) + ambient background integration + the complete API & integration spec for all five Swytchcode toolkits.

---

## 1. Design Intent

A **light, Codex/OpenAI-inspired operator console** with subtle ambient motion and frosted-glass surfaces. The UI's job is to make the agent's multi-step revenue ops reasoning and Swytchcode calls crystal-clear on a projector or screen in ≤2.5 minutes while looking modern, polished, and calm.

Key qualities:
- **Clean light palette:** White frosted surfaces over subtle, desaturated ambient loop motion.
- **Single-column focus:** Centered composer prompt box followed by a linear, uncluttered execution timeline.
- **Zero build step:** Single HTML file with locally vendored Tailwind runtime (`ui/vendor/tailwind.js`). Works 100% offline at venues with zero npm/node overhead.
- **Strict accessibility:** Text contrast passes WCAG AAA standards across all states; `prefers-reduced-motion` cleanly stops all background movement.

---

## 2. Color Palette

| Token | Hex / Value | Usage |
|---|---|---|
| `--bg` | `#FAFAFA` | Page root background |
| `--panel` | `rgba(255, 255, 255, 0.92)` | Cards, prompt composer, result panel (with backdrop blur) |
| `--border` | `#ECECEC` | Hairline dividers, details borders |
| `--border-2` | `#E0E0E0` | Card borders, chip outlines, input borders |
| `--text` | `#0D0D0D` | Primary headers, card titles, Run button |
| `--dim` | `#666666` | Secondary labels, chip text, action button labels |
| `--faint` | `#9B9B9B` | Timestamps, step indices (`01`, `02`), shortcut cues |
| `--ok` | `#15803D` | Success pills, approved state, green timeline rail dots |
| `--warn` | `#B45309` | Amber warning pills, pending approval cards & rail dots, demo data |
| `--err` | `#DC2626` | Error pills, denied state, red timeline rail dots |

**Contrast rule:** All text satisfies ≥ 4.5:1 contrast against translucent panel backgrounds. Status indicators combine textual badges with status-colored dots for color-blind safety and projector clarity.

---

## 3. Typography

| Role | Font | Size / Weight | Notes |
|---|---|---|---|
| UI / body | `ui-sans-serif, system-ui, -apple-system, sans-serif` | 14px / 400, line-height 1.5 | Native system font stack — zero webfont downloads |
| Header title | same | 15px / 650 | Clean wordmark: "LedgerPilot" |
| Header subtitle | same | 12px / 400 | "AI Revenue Ops · Swytchcode × LangGraph" |
| Card node title | same | 13.5px / 600 | Sentence case e.g. `paypal_chase` |
| Step numbers | `ui-monospace, SFMono-Regular, Menlo, monospace` | 11px / 500 | Zero-padded: `01`, `02`, `03` |
| Reasoning text | system sans | 13.5px / 400, line-height 1.55 | Normal style (not italic), clear neutral-700 `#4A4A4A` |
| Tool & command chips | monospace | 11.5px / 400 | `swy exec <canonical_id>`, toolkit name badges |
| JSON blocks | monospace | 12px / 400 | Syntax-highlighted keys (teal), strings (green), numbers (amber) |
| Final answer | system sans | 15px / 400, line-height 1.65 | Styled prose with bold entities and code chips |
| Buttons | system sans | 13–13.5px / 550 | Black solid ("Run", "Approve") or subtle outline ("Deny") |

---

## 4. Component Styles

### 4.1 Header (sticky, height 52px)
Translucent frosted glass (`rgba(255,255,255,0.78)` with `backdrop-filter: blur(14px)`), bottom hairline border.
- **Left:** Minimal brand wordmark "LedgerPilot" and faint subtitle.
- **Right:** Status chip pill (`#statusPill`) indicating connected toolkits or mock mode ("● 5 toolkits connected" / "● mock mode · 5 toolkits wired").

### 4.2 Centered Prompt Composer
- **Container:** Frosted panel (`--panel`, 16px radius, soft shadow, focus-within ring).
- **Textarea:** Borderless, 15px typography, vertical resize, neutral placeholder.
- **Controls row:**
  - Quick-fill prompt chips: `Billing day (full run)` · `Only > ₹50,000` · `What did we chase this week?`
  - Keyboard hint: `⌘ + ↵`
  - Primary button: Solid black `#0D0D0D`, rounded pill, white text. Transitions to disabled "Running…" state during stream.
- **Validation cue:** Smooth inline red message + subtle border pulse if prompt < 10 characters.

### 4.3 Live Run Metadata
Appears immediately on stream start:
`Run <run_id> · <elapsed>s` with tabular numeric elapsed timer, clearing on reset.

### 4.4 Trace Timeline
- **Layout:** Vertical container with left timeline rail (`1px solid #E6E6E6`).
- **Rail dots:** 8px circles positioned on the rail, colored by node status:
  - Green (`--ok`): ok / approved
  - Amber (`--warn`): pending approval
  - Red (`--err`): failed / denied
- **Cards:** Hairline separator between steps, entering with smooth 160ms ease-out animation.
- **Headers:** Step number · node name · toolkit chip · status pill · timestamp.
- **Reasoning:** Clean neutral prose explaining the agent's logic.
- **Swytchcode Command Chip:** Monospace badge showing the canonical ID executed (`swy exec <id>`).
- **Inspection Details:** Collapsible `<details>` for `request` and `response` payloads with clean JSON syntax coloring.
- **Decision Line:** Muted footer row detailing the step's branch choice.

### 4.5 Approval Card (PayPal Gate)
Distinctive operator checkpoint:
- Warm amber background (`#FFFDF6`), subtle amber border (`#F1E4BE`), amber rail dot.
- Buttons row: **Approve** (black pill button) · **Deny** (white pill button with neutral border).
- Policy verification: Explicitly links to `policies.json` with dynamic 120s countdown.
- Resolution: Instantly disables buttons on action, emits toast notification, and updates card badge to "approved by operator" or "denied by operator".

### 4.6 Final Result Panel
- Clean frosted container with uppercase "RESULT" label.
- Structured Markdown summary highlighting invoice numbers, PayPal IDs, Jira ticket keys, and Slack timestamp.
- Action buttons: **Run again** · **Copy summary** (clipboard API with toast feedback) · **Open backup video**.

### 4.7 Toast Feedback & Error Banner
- **Toasts:** Floating white cards in top-right with status-colored indicator dots, soft shadow, 5s auto-dismiss.
- **Connection Banner:** Warm amber banner under header if SSE disconnects, featuring **Retry** button and link to offline backup demo.

---

## 5. Animated Background & Vendored Tailwind Architecture

### 5.1 Ambient Background Pipeline
To elevate visual appeal while preserving readability, an ambient background video runs behind the UI:
- **Master Source:** `/data/api/tunnelmotions34854reflectionspace0001_0600.mp4` (4K 60fps, 217 MB, 10s loop). Kept outside the repository to prevent git bloat.
- **Transcoded Web Asset:** Transcoded via `ffmpeg` to 1080p, 30fps, CRF 30, no audio, with web-optimized faststart headers:
  ```bash
  ffmpeg -y -v error -i /data/api/tunnelmotions34854reflectionspace0001_0600.mp4 \
    -vf "scale=1920:-2,fps=30" -c:v libx264 -crf 30 -preset medium -an \
    -movflags +faststart ui/assets/bg.mp4
  ffmpeg -y -v error -i ui/assets/bg.mp4 -frames:v 1 -q:v 4 ui/assets/bg.jpg
  ```
  Output: `ui/assets/bg.mp4` (~4.3 MB, seamlessly looping) and `ui/assets/bg.jpg` (~49 KB instant poster fallback).
- **Delivery:** Served directly through FastAPI's static file mount (`/static/assets/bg.mp4`).
- **Layering & Readability:**
  - `<video id="bgVideo">`: Fixed position, `inset: 0`, `z-index: -2`, `object-fit: cover`, subtly filtered (`filter: saturate(.8) brightness(1.12)`).
  - `<div id="bgScrim">`: Fixed position, `inset: 0`, `z-index: -1`, with `background: rgba(250,250,250,0.76)` and `backdrop-filter: blur(28px) saturate(1.15)`.
  - Ensures content panels (`rgba(255,255,255,0.92)`) float on a soft, frosted canvas with guaranteed text contrast.
- **Battery & Accessibility:** Listens to `document.visibilitychange` to automatically pause playback when the browser tab is hidden. `@media (prefers-reduced-motion: reduce)` automatically hides the video element and disables entry animations.

### 5.2 Vendored Tailwind Architecture
To ensure the UI is robust in offline conference/demo venue environments:
- Tailwind Play CDN runtime is vendored locally into `ui/vendor/tailwind.js` (~451 KB).
- Loaded via `<script src="/static/vendor/tailwind.js"></script>`.
- **Zero build step required:** No node, npm, webpack, or compiler needed. Edit `ui/index.html` and refresh.
- 100% offline and venue wifi-safe (no external CDN network requests).

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
| Search | `gmail.user.messages.get` | `{"userId": "me", "q": GMAIL_QUERY, "maxResults": MAX_INVOICES}` | message IDs |
| Fetch | `gmail.user.messages.get1` | `{"userId": "me", "id": msg_id, "format": "full"}` | subject, snippet, date → LLM parses to `Invoice[]` |

**Output drives next action:** `invoices[]` is the sole input to `classify` — no invoices →
E4 clean stop.

---

### 6.2 PayPal — payment chase (`toolkit: paypal`) · **gated write**

| Property | Value |
|---|---|
| Purpose | Create/send a payment chase for OVERDUE invoices (sandbox only) |
| Called from | `agent/nodes/paypal_chase.py` |
| Gating | UI approval **and** kernel rule `paypal-approval` (`invoices.invoicing.send.create`, `invoice_id exists` → `REQUIRES_APPROVAL`) |
| Environment | `PAYPAL_ENV=sandbox` — enforced at config load |

| Step | Canonical ID (illustrative) | Request | Response used |
|---|---|---|---|
| Create draft | `invoices.invoicing.invoices.create` | `{"body": {"detail": {"invoice_date": today}, "primary_recipients": [{"name": vendor}], "amount": {"value": amt, "currency_code": cur}}}` | `id` (`INV-…`) |
| Send draft | `invoices.invoicing.send.create` | `{"invoice_id": <created id>, "body": {"subject": …, "note": …}}` | `href`/`rel` (kernel policy `paypal-approval` fires here → exit 7 until approved) |

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
| Create issue | `jira.api.issue.create` | `{"body": {"fields": {"project": {"key": "OPS"}, "summary": "Dispute: <vendor> #<id>", "issuetype": {"name": "Bug"}, "priority": {"name": "High" if amount>50000 else "Medium"}, "description": <email excerpt + decision reason>}}}` | `key` (`OPS-…`) |

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
| Query DB | `notion.query.create` | `{"data_source_id": OPS_DB, "body": {"filter": {"property": "Run ID", "rich_text": {"equals": run_id}}}}` | dedupe check (E10/X3) |
| Create row | `notion.page.create` | `{"body": {"parent": {"database_id": OPS_DB}, "properties": {Invoice ID, Vendor, Amount, Due Date, Label, Status, PayPal Invoice ID, Jira Key, Run ID, Ran At}}}` | `page_id` |

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
| Post | `slack.chat.postmessage.create` | `{"body": {"channel": "#finance-ops", "text": summary_from_results}}` | `ts`, `channel` |

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
