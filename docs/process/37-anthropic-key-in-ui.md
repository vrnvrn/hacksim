# Commit 37: in-UI Anthropic API key paste, localhost-gated

## What changed

Users running HackSim locally can now paste their Anthropic API key into
a password field in the home page Settings popover instead of having to
export `ANTHROPIC_API_KEY` in the shell. The key flows from the browser
through the orchestrator into each spawned worker process and never
lands in the SSE buffer, the snapshot, the request repr, or any log
line. The same field is refused with HTTP 403 from any non-localhost
origin so a hosted deployment cannot turn into a credential paste box.

Files added:

- `apps/web/lib/anthropic-key.ts`: `getAnthropicKey`, `setAnthropicKey`,
  `isLocalhostOrigin`. Backed by `sessionStorage` so the key dies when
  the tab closes and never reaches `localStorage`.
- `packages/orchestrator/tests/test_api_anthropic_key.py`: six tests
  covering the localhost gate, the rejection path, and three never-leak
  guarantees (no key in the SSE buffer, no key in the snapshot, no key
  in the request repr).

Files changed:

- `packages/orchestrator/spawner.py`: `spawn_role` accepts
  `extra_env: dict[str, str] | None`. The mapping is layered onto the
  worker process env after the AXL discovery vars so the key only
  reaches workers, never the AXL nodes themselves.
- `packages/orchestrator/controller.py`: `SimController.__init__`
  accepts `extra_env`, threaded into all four `spawn_role` calls
  (organiser, designers, builders, judges).
- `packages/orchestrator/api.py`: adds `_LOCAL_HOSTS`,
  `_is_localhost_request`, and an `anthropic_api_key: SecretStr | None`
  field on `CreateSimRequest` that is excluded from `model_dump`. The
  POST handler extracts the key with `get_secret_value`, gates by
  localhost, and passes it to `SimController` via `extra_env`. The
  `sim.created` event publishes `"llm": "anthropic"` or `"stub"` so the
  UI can surface which backend is in play without ever serialising the
  key itself.
- `apps/web/components/HeroPrompt.tsx`: the Settings popover now renders
  a `KeyRow` that only mounts when `window.location.hostname` is a
  loopback. The input is `type="password"` with a Show/Hide toggle and
  a Clear button, and writes through to `sessionStorage`. Submit reads
  the key from `sessionStorage` and only attaches it when the page
  origin is also loopback.
- `apps/web/components/HeroExamplesAside.tsx`: the same forward path,
  so clicking a preset reuses whatever key the user already pasted.
- `apps/web/components/Faq.tsx`: the existing "Do I need an Anthropic
  API key?" entry now documents the password-input route alongside the
  env var route, naming `SecretStr`, the localhost gate, and the 403.

## Why

Two reasons.

First, demo ergonomics. A judge or visitor who wants to see the real
LLM path without rebooting `make demo` should not have to drop into a
shell. A password input in the settings popover is the lowest-friction
on-ramp; sessionStorage scoping means the key is gone the moment the
tab closes.

Second, defensive defaults. A naive "paste your API key here" field is
a credential harvesting vector when the page is hosted publicly. The
orchestrator independently refuses the field with 403 from any
non-loopback origin, the frontend hides the input on any non-localhost
page, and Pydantic `SecretStr` keeps the value out of `repr` and
`model_dump`. Three independent defences cover the case where any one
of them is bypassed.

## How to verify

Backend:

```
.venv/bin/pytest packages/orchestrator/tests/test_api_anthropic_key.py -v
```

Six tests pass. The full backend suite still passes (105 tests).

Frontend:

```
cd apps/web && bun run test
cd apps/web && bun run typecheck
cd apps/web && bun run build
```

20 test files, 65 tests pass; tsc clean; build succeeds.

Manual smoke (localhost):

1. `make demo`, open `http://localhost:3000`.
2. Click Settings. The "Anthropic API key" row appears.
3. Paste a real `sk-ant-...` key, click Show to confirm, click Done.
4. Type a prompt and click Spin up sim.
5. The sim page header reads `live · llm: anthropic`. Role workers call
   Claude haiku 4.5 instead of the deterministic stub.
6. Open the orchestrator log. The key never appears.

Manual smoke (refusal path):

```
curl -sX POST http://127.0.0.1:8000/api/sim \
  -H 'X-Forwarded-For: 203.0.113.42' \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"x","anthropic_api_key":"sk-ant-fake"}'
```

Returns 403 with `"anthropic_api_key is only accepted on localhost..."`.

## AXL surface used

None on this commit; the change lives entirely in the orchestrator
process boundary and the frontend. The AXL nodes are unchanged. The
key only reaches role worker processes through `extra_env`, layered on
top of the AXL discovery env vars but separate from them.

## What comes next

A `make demo` flag that mirrors the env var into a sentinel so the UI
can surface a "key already configured on host" hint in Settings, plus
a free-LLM fallback through the Vercel AI Gateway for a hosted demo
where local key pasting is not on the table. Tracked under §19b in
`refs/PLAN.md`.
