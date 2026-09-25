#!/usr/bin/env bash
# Verify every canonical ID in .swytchcode/tooling.json resolves via `swy info` (Gate B companion).
# Run AFTER `swy get` has fetched provider bundles. Exit 1 if any ID is missing.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

command -v swy >/dev/null 2>&1 || { echo "✗ 'swy' not on PATH — install first (scripts/setup.sh)"; exit 1; }

IDS=$(python3 - <<'PY'
import json
cfg = json.load(open(".swytchcode/tooling.json"))
for tk, info in cfg.get("toolkits", {}).items():
    for tool in info.get("tools", []):
        print(tool["canonical_id"])
PY
)

pass=0; fail=0; failed_ids=""
printf "%-34s %-6s %s\n" "CANONICAL ID" "RESULT" "DETAIL"
printf -- "------------------------------------------------------------\n"
for id in $IDS; do
  out=$(swy info "$id" 2>&1)
  if [ $? -eq 0 ]; then
    printf "%-34s \033[32m%-6s\033[0m %s\n" "$id" "PASS" "$(echo "$out" | head -1 | cut -c1-46)"
    pass=$((pass+1))
  else
    printf "%-34s \033[31m%-6s\033[0m %s\n" "$id" "FAIL" "$(echo "$out" | grep -v '^\s*$' | head -1 | cut -c1-46)"
    fail=$((fail+1)); failed_ids="$failed_ids $id"
  fi
done
printf -- "------------------------------------------------------------\n"
echo "$pass/$((pass+fail)) canonical IDs verified"
if [ "$fail" -gt 0 ]; then
  echo "Missing:$failed_ids"
  echo "Fix: swy get <provider>  (or the ID differs from spec — check 'swy search <toolkit>')"
  exit 1
fi
echo "Gate B (IDs): PASS"
