#!/usr/bin/env bash
# No-hardcoded-color check (K1 handoff, Check 1b): components reference var(--token), not a raw
# hex color. tokens.css itself is the source of truth and is excluded. Every hit must be one of
# the documented baseline exceptions below (a `var(--token, #fallback)` defended fallback) — a
# NEW hit not in the baseline is a defect. Run: bash frontend/scripts/check-hardcoded-colors.sh

set -euo pipefail
cd "$(dirname "$0")/.."

# documented baseline: `var(--token, #hex)` fallback where --token is already defined elsewhere
# (the fallback is unreachable / defended) — see DESIGN.md Findings + K1 dev-to-qa notes.
BASELINE='src/admin/AdminLayout.vue:473:  color: var(--on-accent, #fff);
src/admin/views/DashboardView.vue:963:  color: var(--side-text-hi, #fff);'

HITS=$(grep -rnE '#[0-9a-fA-F]{3,8}\b' src --include='*.vue' --include='*.css' | grep -v 'src/styles/tokens.css' || true)

echo "Hardcoded hex colors found (excluding src/styles/tokens.css):"
if [ -z "$HITS" ]; then
  echo "  (none)"
else
  echo "$HITS" | sed 's/^/  /'
fi

NEW=$(comm -23 <(echo "$HITS" | sort) <(echo "$BASELINE" | sort))

if [ -n "$NEW" ]; then
  echo
  echo "NEW hardcoded color(s) beyond the documented baseline:"
  echo "$NEW" | sed 's/^/  /'
  exit 1
fi

echo
echo "PASS — no hardcoded color beyond the documented baseline."
