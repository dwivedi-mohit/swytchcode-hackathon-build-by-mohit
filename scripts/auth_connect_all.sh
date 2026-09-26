#!/usr/bin/env bash
# Run this in YOUR terminal (browser opens for each provider, one at a time).
# Prereqs: gmail/slack/notion = any account; jira = an Atlassian account that
# ALREADY has a free Jira site (else Atlassian shows "Access denied").
# paypal is skipped: its Swytchcode OAuth app is broken upstream
# ("invalid client_ID or redirect_uri") and invoicing works without auth.
# Pass extra provider names (e.g. ./scripts/auth_connect_all.sh paypal) to attempt them anyway.
set -u
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")/.."

PROVIDERS=(gmail slack notion jira "$@")

for p in "${PROVIDERS[@]}"; do
  echo "=== auth connect $p ==="
  swy auth connect "$p" || echo "!! $p connect failed (skipping)"
done

echo
swy auth status
echo
./scripts/smoke_test.py
