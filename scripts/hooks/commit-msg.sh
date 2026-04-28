#!/usr/bin/env bash
# HackSim commit-msg hook.
# Rejects co-author trailers, "generated with" attributions, em or en dashes,
# and rhetorical contrast structures inside the commit message itself.
# See refs/PLAN.md section 17. Patterns built from hex escapes so this script
# does not flag itself when staged. POSIX ERE under LC_ALL=C for cross-platform.

set -uo pipefail

MSG_FILE="$1"

fail() {
  echo "writing-rule violation in commit message: $1" >&2
  echo "edit the commit message and try again. see refs/PLAN.md section 17." >&2
  exit 1
}

em=$(printf '\xe2\x80\x94')
en=$(printf '\xe2\x80\x93')
nj=$(printf '\x6e\x6f\x74 \x6a\x75\x73\x74')
no=$(printf '\x4e\x6f\x74 \x6f\x6e\x6c\x79')
ca=$(printf '\x63\x6f-\x61\x75\x74\x68\x6f\x72\x65\x64-\x62\x79')
gw=$(printf '\x67\x65\x6e\x65\x72\x61\x74\x65\x64 \x77\x69\x74\x68')

if LC_ALL=C grep -qiE "${ca}:" "$MSG_FILE"; then
  fail "co-author trailer"
fi
if LC_ALL=C grep -qiE "${gw}" "$MSG_FILE"; then
  fail "generated-with attribution"
fi
if LC_ALL=C grep -qE "(${em}|${en})" "$MSG_FILE"; then
  fail "em or en dash"
fi
if LC_ALL=C grep -qiE "(^|[^A-Za-z])${nj}([^A-Za-z]|\$)" "$MSG_FILE"; then
  fail "rhetorical contrast (lowercase)"
fi
if LC_ALL=C grep -qE "(^|[^A-Za-z])${no}([^A-Za-z]|\$)" "$MSG_FILE"; then
  fail "rhetorical contrast (titlecase)"
fi

exit 0
