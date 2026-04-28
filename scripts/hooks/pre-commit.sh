#!/usr/bin/env bash
# HackSim pre-commit writing-rules enforcer.
# See refs/PLAN.md section 17. The forbidden patterns are constructed from hex
# escapes so this script does not trip its own checks when staged. Uses POSIX
# extended regex so it works with both GNU and BSD grep.

set -uo pipefail

DIFF="$(git diff --cached -U0)"

fail() {
  echo "writing-rule violation in staged diff: $1" >&2
  echo "fix the offending line and re-stage. see refs/PLAN.md section 17." >&2
  exit 1
}

em=$(printf '\xe2\x80\x94')
en=$(printf '\xe2\x80\x93')
nj=$(printf '\x6e\x6f\x74 \x6a\x75\x73\x74')
no=$(printf '\x4e\x6f\x74 \x6f\x6e\x6c\x79')

# Em dash or en dash anywhere in any added line.
if printf '%s' "$DIFF" | grep -qE "^\+.*[${em}${en}]"; then
  fail "em or en dash"
fi

# Lowercase rhetorical contrast as a whole word.
if printf '%s' "$DIFF" | grep -qiE "^\+.*(^|[^A-Za-z])${nj}([^A-Za-z]|\$)"; then
  fail "rhetorical contrast (lowercase)"
fi

# Titlecase rhetorical contrast as a whole word.
if printf '%s' "$DIFF" | grep -qE "^\+.*(^|[^A-Za-z])${no}([^A-Za-z]|\$)"; then
  fail "rhetorical contrast (titlecase)"
fi

exit 0
