# Submission Checklist

**Product:** LedgerPilot — AI Revenue Operations Agent · Track 6 · Solo builder
**Event:** Build with Swytchcode, Sep 26 2026, Thoughtworks Gurgaon
**Deadline:** 15:30 on Commudle — `https://www.commudle.com/builds/create?campaign=BuildWithSwytchcode`
**Target completion:** 15:15 (per `BUILD.md` §3)

Tick every box before hitting submit. Anything unchecked = do not submit yet (except items marked
*optional*).

---

## 1. Repo & code (required by event rules)

- [ ] Repo is **public** and loads without login
- [ ] Fresh clone + README instructions reaches a working demo in <10 min
- [ ] `.env` absent from repo; `.env.example` present with empty placeholders
- [ ] Git history audit clean — no keys/tokens/secrets ever committed
      (`git log -p | grep -iE "api[_-]?key|secret|token"` → only example placeholders)
- [ ] `.swytchcode/tooling.json` committed (proof of enabled toolkits)
- [ ] `.swytchcode/policies.json` committed (evidence) **and** `.swytchcode/integrations/policies.json` validated (`swy policy validate`) — kernel-enforced PayPal approval gate
- [ ] `seed/invoices.json` committed (demo data, 4 invoices)
- [ ] No large binaries in git (backup mp4 gitignored)

## 2. README (explicit event requirement)

- [ ] What LedgerPilot does (1–2 sentences + screenshot/GIF of the trace UI)
- [ ] Agent flow / architecture diagram (Mermaid renders on GitHub)
- [ ] Setup instructions: prerequisites → `./scripts/setup.sh` → auth → `.env` →
      `python -m server.main` → open `http://localhost:8000`
- [ ] The 3 demo prompts listed for anyone to reproduce
- [ ] Troubleshooting (seed fallback, `MOCK_LLM=1`, wifi hotspot)
- [ ] Event attribution: Build with Swytchcode × KNOTiC, Track 6, solo entry

## 3. Swytchcode integration evidence (30% of rubric)

- [ ] **≥3 toolkits** invoked through Swytchcode — target 5 (gmail, paypal, jira, notion, slack)
- [ ] Canonical tool IDs visible in README evidence block (`tooling.json` excerpt)
- [ ] Calls chained agentically — each tool's output feeds the next step
      (paypal → notion → slack; jira → notion → slack)
- [ ] `swy audit` / execution-layer proof available if asked
- [ ] Approval policy demonstration for PayPal works live

**Self-score check against rubric:** API integration 30% ✅ · technical 25% · innovation 20% ·
functionality 10% · impact 10% · UX 5% — evidence for each:

| Rubric line | Where the evidence lives |
|---|---|
| Swytchcode API integration (30) | README evidence block + live trace + tooling.json |
| Technical complexity (25) | LangGraph conditional graph + SSE streaming + approval gate (TECHNICAL_ARCHITECTURE) |
| Innovation (20) | human-in-the-loop policy gate + honest degradation (PRD F16, SECURITY §4) |
| Functionality (10) | Gate E live run: real PayPal ID, Slack ts, Notion page |
| Impact (10) | PRD §1 problem + §7 metrics |
| UX (5) | FRONTEND_SPEC trace UI, mobile check |

## 4. Demo readiness

- [ ] Full run ≤3 min without crash (Gate F)
- [ ] Failure drills passed: E2, E3, E6, E10, X11, E9
- [ ] Backup video recorded (`docs/demo/run.mp4`) and linked in README
- [ ] Screenshots captured: (a) approval card, (b) full trace, (c) live results
- [ ] Demo laptop: server runs, browser bookmarked to `localhost:8000`, fullscreen zoomed for projector
- [ ] Phone hotspot tested as wifi fallback

## 5. Pre-submit form prep (have these ready in a text file)

- [ ] Public repo URL
- [ ] Project name: **LedgerPilot**
- [ ] One-line pitch: *"Agent that reads invoice emails, chases overdue payments through
      PayPal behind a human-approval gate, escalates disputes to Jira, logs to Notion and
      summarizes in Slack — with a live audit trace."*
- [ ] Description (~150 words) — start from PRD §2 vision
- [ ] Track: 6 · Solo
- [ ] Tech stack line: Python, LangGraph, FastAPI/SSE, Swytchcode Runtime SDK, single-file UI
- [ ] Screenshots/video attached per form fields

## 6. Act of submitting (14:50–15:10)

- [ ] Commudle submission created and **confirmed**
- [ ] All links in the submission open correctly (click each once)
- [ ] Submission receipt/screenshot saved
- [ ] Track form (if not yet done, `https://forms.gle/DZz8fzQh8PNxcbPXA`) — irreversibly Track 6

## 7. After submit

- [ ] Re-walk this checklist once (anything regressed after last edit)
- [ ] Repo left in demo-able state for Q&A at closing ceremony
- [ ] Optional T38 social post with repo link

---

**Sign-off:** Gate G in `BUILD.md` marks submission confirmed ≤15:30.
If time forces triage: repo + README + ≥3 toolkits + form are the non-negotiable minimum.
