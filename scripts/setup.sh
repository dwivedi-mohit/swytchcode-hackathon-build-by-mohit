#!/usr/bin/env bash
# LedgerPilot setup: Swytchcode init + 5 toolkits + tools + doctor (T01)
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n\033[1;35m== %s\033[0m\n' "$1"; }
fail() { printf '\033[1;31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

say "0/5 secret audit"
if git rev-parse --git-dir >/dev/null 2>&1; then
  if git ls-files -z | xargs -0 grep -lEi '(api[_-]?key|secret|token|password)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9_\-]{16,}' 2>/dev/null; then
    fail "possible secret in tracked files — remove before continuing (T01)"
  fi
fi
echo "✓ no hardcoded secrets found"

say "1/5 swytchcode CLI"
if ! command -v swy >/dev/null 2>&1; then
  echo "'swy' not found — installing via npm (v2.23.7 verified)…"
  if npm install -g swytchcode 2>/dev/null; then :; else
    npm config set prefix "$HOME/.local" && npm install -g swytchcode || fail "npm install failed — install Node.js first"
    export PATH="$HOME/.local/bin:$PATH"
    echo "note: add 'export PATH=\"\$HOME/.local/bin:\$PATH\"' to your shell profile"
  fi
fi
swy --version || fail "'swy' install broken"

say "2/5 project + toolkits"
if [ ! -f .swytchcode/tooling.json ]; then
  swy init --non-interactive --editor none --mode sandbox || true
fi
for t in paypal gmail slack jira notion; do
  swy get "$t" --non-interactive && echo "✓ $t" || echo "✗ $t (continuing — see doctor)"
done
swy bootstrap || true   # fetch everything declared in tooling.json

say "3/5 attach tools"
python3 - <<'PY'
import json, subprocess, sys
cfg = json.load(open(".swytchcode/tooling.json"))
for tk, info in cfg.get("toolkits", {}).items():
    for tool in info.get("tools", []):
        cid = tool["canonical_id"]
        r = subprocess.run(["swy", "add", cid], capture_output=True, text=True)
        print(("✓" if r.returncode == 0 else "✗"), cid, "" if r.returncode == 0 else r.stderr.strip())
PY

say "4/5 policy (kernel-enforced approval gate)"
swy policy validate || true
swy policy list || true

say "5/5 doctor"
swy doctor || true
echo
echo "Next steps:"
echo "  1. swy auth connect paypal   # then gmail slack jira notion (interactive)"
echo "     swy auth status           # confirm connected accounts"
echo "  2. cp .env.example .env      # add GEMINI_API_KEY / GROQ_API_KEY (or MOCK_LLM=1)"
echo "  3. pip install -r requirements.txt"
echo "  4. python scripts/smoke_test.py            # Gate B: floor 3 toolkits PASS"
echo "  5. python scripts/verify_canonical_ids.sh  # every canonical ID resolves"
echo "  6. python -m server.main  →  http://localhost:8000"
