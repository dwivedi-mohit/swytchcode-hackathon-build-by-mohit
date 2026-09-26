#!/usr/bin/env bash
# Run this in YOUR terminal (browser opens for each provider, one at a time).
# Order matters: paypal already works without auth; the rest gate smoke floor (>=3).
set -u
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")/.."

for p in gmail slack notion jira paypal; do
  echo "=== auth connect $p ==="
  swy auth connect "$p" || echo "!! $p connect failed (skipping)"
done

echo
swy auth status
echo
./scripts/smoke_test.py
