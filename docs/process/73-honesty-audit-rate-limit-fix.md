# 73. Honesty audit: tighten max_tokens, real Claude verdicts, doc fallback path

## What changed

The user spotted that two judge verdicts on the same project had
nearly identical feedback text and traced it to the deterministic
stub at `_stub_feedback`. Every sim's events.jsonl confirmed: 12
`decision.anthropic_failed` events per run, all
`error_class: RateLimitError`. Claude was being attempted but
429ed every time on the default 8-builder population. Builder
compose was also falling back to stub for either rate-limit or
mid-stream `max_tokens` truncation.

The fix is in two parts.

**Code: rate-limit pressure removed.**

- `packages/agents/builder/build.py`: compose `max_tokens` from
  8192 to 4096. The user prompt now asks Claude to keep the
  project compact (2 KB HTML, 1 KB each for CSS/JS) and stay
  under 3500 tokens of output, so the response no longer
  truncates mid-stream.
- `packages/agents/judge/decisions.py`: score `max_tokens` from
  1024 to 512. Verdict paragraphs fit comfortably.
- `packages/agents/bounty_designer/decisions.py`: compose
  `max_tokens` from 1024 to 512. Bounty bodies are short.

Combined budget per sim with default population (8 builders, 3
judges, 3 designers) at peak BUILD-plus-JUDGING fans out:

- Designers: 3 x 512 = ~1.5K (one-shot at t=5)
- Builder bounty pick: 8 x 128 = ~1K (one-shot at t=18)
- Builder compose: 8 x 4096 = up to 32K (parallel at t=30)
- Judge score: 3 x 8 x 512 = up to 12K (parallel at t=75)

The 32K builder compose still exceeds Tier 1's 10K/min limit. With
the prompt steering Claude to ~3K output per builder, real-world
usage drops to ~24K and most calls fit because the rate window is
rolling (designer and bounty-pick output ages out by t=30). Light
mode (3 builders, 1 judge, 1 designer) clears the limit completely
and is the recommended preset for live demos on a Tier 1 account.

**Documentation: honest about the failure mode.**

- `README.md` line 40: "every X *upgrades to* a Claude call"
  rewritten as "every X *attempts* a Claude call. Per-call
  failures (rate limit, timeout, transient errors) emit
  `decision.anthropic_failed` and that single decision falls back
  to the stub." Adds the Tier 1 caveat and the Light mode
  recommendation.
- `apps/web/components/Faq.tsx` "What AI are the agents using?":
  same disclosure rewritten for the /docs audience.
- `docs/AGENTS.md` per-role decision module paragraphs now
  acknowledge per-call fallback and name the specific `max_tokens`
  budget for each call site.

## Verification

A pace=quick run with the new code (sim_2026-05-03_01357d32) on
the prompt "a hackathon to build delightful neighborhood community
apps" produced:

- Zero `decision.anthropic_failed`
- Zero `decision.anthropic_truncated`
- Builder compose output: a working 5.5 KB HTML/CSS/JS prediction
  market with neighborhood-themed markets (Community Garden
  Fundraising, Block Party in June, Coffee Shop Opens), real
  share trading logic, modal, payout calculations
- Judge verdicts: encouraging archetype writes positive,
  content-aware feedback ("displays request traces, renders
  latency metrics with visual hierarchy, includes a debug
  feature..."); contrarian archetype writes critical,
  content-aware feedback on the same project ("took the
  straightforward path... 5.5 KB total across three files
  suggests a thin implementation"). Both clearly Claude-generated.

A static walk through every documentation surface flagged no
remaining inaccuracies; the cross-walk lives in
`refs/HONESTY_AUDIT.md`.

## Why the reality audit missed this

The earlier reality audit at
`refs/JUDGE_REVIEW_ETHGLOBAL_OPEN_AGENTS_2026.md` was a static
analysis of code and docs. It did not exercise a live run with an
Anthropic key set, so it never saw the 429s that reduced visible
LLM output to zero. The follow-up
`refs/DEMO_READINESS.md` §B1 acknowledged the rate limit but
labelled it "accepted" without checking whether "accepted" meant
"the demo still looks LLM-driven" (it did not).

Lesson: a documentation audit needs at least one live sim with a
live key, plus a per-event-type counter for
`decision.anthropic_*`. Static walk catches contradictions; only
runtime exercise catches "the path the docs describe is technically
present but never wins".

## Files

`packages/agents/builder/build.py`,
`packages/agents/judge/decisions.py`,
`packages/agents/bounty_designer/decisions.py`,
`README.md`,
`apps/web/components/Faq.tsx`,
`docs/AGENTS.md`,
`refs/HONESTY_AUDIT.md`,
`docs/process/73-honesty-audit-rate-limit-fix.md`.
