# Security patches, 2026-10-22

## Summary

`pip-audit` and `pnpm audit` reported known vulnerabilities in the Python lockfile (`requirements-lock.txt`) and in the web app (`apps/web`). This change updates the affected packages to patched releases in the same major version. Two earlier fixes from the same day (CI Node.js runtime and `certifi`) are listed below for completeness.

Audit counts:

| Scope | Before | After |
| --- | --- | --- |
| Python (`requirements-lock.txt`, pip-audit) | 31 advisories in 5 packages | 0 |
| Web (`apps/web`, pnpm audit) | 70 (5 critical, 36 high, 25 moderate, 4 low) | 8 (2 critical, 3 high, 3 moderate, 0 low) |

The 8 remaining web findings are explained under "Not fixed".

## Python changes (`requirements-lock.txt`)

Regenerated with the command in the lockfile header (`pip-compile ... --upgrade-package`), so only the listed packages moved.

| Package | From | To | Advisories | Why it matters here |
| --- | --- | --- | --- | --- |
| aiohttp | 3.13.5 | 3.14.4 | 22 advisories, including CVE-2026-69243 (request smuggling via WebSocket upgrade), CVE-2026-54275 (TLS SNI check bypass on connection reuse), CVE-2026-69244 (out-of-bounds read in C response parser), CVE-2026-111750 (pure Python parser request smuggling), CVE-2026-54273/54274/54278 (memory exhaustion), CVE-2026-47265 and CVE-2026-54276 (cookies and digest auth sent across origins on redirect) | Used by the judge agent's MCP service (`packages/agents/judge/mcp_service.py`). |
| yarl | 1.23.0 | 1.25.1 | none directly; required by aiohttp 3.14.4 | Pulled in by the aiohttp bump. |
| anyio | 4.13.0 | 4.14.2 | CVE-2026-63374 (TLS hostname check with IDN names), CVE-2026-64847 (process pool workers can hang on undrained stderr) | Async runtime under FastAPI, Starlette, httpx and the Anthropic SDK. |
| idna | 3.13 | 3.15 | CVE-2026-45409 (CPU denial of service on crafted input; incomplete fix of CVE-2024-3651) | Used by httpx and anyio for hostname handling. |
| multidict | 6.7.1 | 6.9.1 | CVE-2026-104874 (reference leak in C extension, remote memory growth) | Header storage for aiohttp and yarl. |
| starlette | 1.0.0 | 1.3.1 | CVE-2026-48710 and CVE-2026-54282 (unvalidated Host header and path used to rebuild `request.url`), CVE-2026-48817 (HTTPEndpoint method dispatch), CVE-2026-48818 (StaticFiles SSRF on Windows), CVE-2026-54283 (form limits not enforced for urlencoded bodies) | The orchestrator HTTP API runs on FastAPI, which is built on Starlette. |

## Web changes (`apps/web`)

Direct dependencies raised in `package.json` (same major). Transitive packages were raised with scoped `pnpm.overrides` entries that only match vulnerable versions and stay inside the same major. The lockfile was regenerated with pnpm 9.15.0, the version pinned in `packageManager`.

| Package | From | To | Advisories | Why it matters here |
| --- | --- | --- | --- | --- |
| next (direct) | 15.5.15 | 15.5.28 | 25 advisories, including GHSA-p293-qw3h-jr36 / CVE-2026-75604 and GHSA-2xp9-vwfh-vxw4 (critical, unauthenticated RCE), CVE-2026-45109, CVE-2026-44573/44574/44575 (middleware bypass), CVE-2026-44578, CVE-2026-64645, CVE-2026-64649 (SSRF), CVE-2026-44580/44581 (XSS), CVE-2026-94484/94543 (cache poisoning) | The web app is a Next.js server with API routes. |
| vitest (direct, dev) | 3.2.4 | 3.2.7 | CVE-2026-47429 (critical, file read and execution when Vitest UI server is listening) | Test runner used in CI and locally. |
| vite (direct, dev) | 6.4.2 | 6.4.4 | CVE-2026-53571, CVE-2026-112942 (fs.deny / existence check bypass on Windows), CVE-2026-112943/112944 (launch-editor command handling), CVE-2026-112945, CVE-2026-112946, CVE-2026-53632 | Dev server used by Vitest. |
| postcss (direct, dev) | 8.5.13 | 8.5.31 | CVE-2026-73646 (path traversal in source map auto-loading), CVE-2026-69153 | CSS build pipeline. |
| nanoid | 3.3.12 | 3.3.20 | CVE-2026-67213, CVE-2026-67214 (infinite loops) | Pulled in by postcss; fixed by the postcss bump. |
| browserslist | 4.28.2 | 4.29.4 | CVE-2026-73088 (crash / prototype write on untrusted config), CVE-2026-73089 (unbounded memory) | Build tooling. Required `caniuse-lite` 1.0.30001816 and `electron-to-chromium` 1.5.459 (data packages). |
| baseline-browser-mapping | 2.10.25 | 2.11.30 | CVE-2026-45819 (process exit on invalid input) | Build tooling, under browserslist. |
| brace-expansion | 1.1.14 / 5.0.5 | 1.1.21 / 5.0.12 | CVE-2026-13149, CVE-2026-14257, CVE-2026-69152, CVE-2026-102276, CVE-2026-102277, CVE-2026-102278, CVE-2026-45149 (denial of service) | Glob matching in ESLint and tooling. |
| form-data | 4.0.5 | 4.0.6 | CVE-2026-12143 (CRLF injection in multipart field names) | Pulled in by test tooling (jsdom). |
| js-yaml | 4.1.1 | 4.3.2 | CVE-2026-53550, CVE-2026-59869, CVE-2026-84375, GHSA-5p4m-2wfm-xmqj (CPU denial of service) | ESLint config loading. |
| ws | 8.20.0 | 8.22.0 | CVE-2026-48779 (memory exhaustion), CVE-2026-45736 (uninitialized memory disclosure) | WebSocket library used by jsdom and dev tooling. |
| source-map-js | 1.2.1 | 1.2.2 | CVE-2026-93749 (event loop denial of service) | Build tooling. |
| @babel/core | 7.29.0 | 7.29.7 | CVE-2026-49356 (file read via sourceMappingURL) | Build tooling. |

## Earlier fixes today (commit 9c03f36)

| Component | From | To | Reason |
| --- | --- | --- | --- |
| Node.js in CI (`.github/workflows/ci.yml`) | 20 | 22.23.4 | Node.js security releases of 21 Oct 2026 (CVE-2026-111497 and 9 others) fix a Brotli decoder RCE reachable through `fetch()` and two TLS certificate validation bypasses. Node 20 is end of life and gets no fix. |
| certifi | 2026.4.22 | 2026.10.19 | eMudhra CA compromise: private keys for 8 intermediate CAs were recoverable, so fraudulent certificates could be issued. certifi 2026.10.19 removes those intermediates. |

## Verification

Baseline was recorded before any change, then the same commands were run again after.

| Check | Command | Before | After |
| --- | --- | --- | --- |
| Ruff | `.venv/bin/python -m ruff check packages/ tests/` | pass | pass |
| Pytest (unit + component) | `.venv/bin/python -m pytest packages/ -q` | 302 passed | 302 passed |
| Python audit | `uvx pip-audit -r requirements-lock.txt --no-deps --disable-pip` | 31 advisories | none found |
| Frozen install | `pnpm install --frozen-lockfile` (pnpm 9.15.0) | pass | pass |
| TypeScript | `npx tsc --noEmit` | pass | pass |
| ESLint | `pnpm lint` | pass | pass |
| Vitest | `pnpm vitest --run` | 27 files, 94 tests passed | 27 files, 94 tests passed |
| Next.js build | `pnpm build` | pass | pass |
| Web audit | `pnpm audit` | 70 | 8 |

Notes:

- Python checks ran on Python 3.12 (the CI version). Web checks ran locally on Node 26 with pnpm 9.15.0; CI uses Node 22.23.4.
- The integration job (`pytest tests/integration/`) was not run. It needs the AXL Go binary built from the `third_party/axl` submodule. CI runs it.
- After the upgrade, Starlette 1.3.1 emits one new deprecation warning in tests: using `httpx` with `starlette.testclient` is deprecated in favor of `httpx2`. Tests still pass.

## Not fixed

| Package | Version | Advisories | Reason |
| --- | --- | --- | --- |
| tinypool | 1.1.1 | CVE-2026-104848, CVE-2026-104849 (critical, prototype pollution to RCE) | The fix is in tinypool 2.x. Vitest 3.x requires `tinypool ^1.1.1`, and no 1.x fix exists. Fixing it needs Vitest 4 or later (major upgrade). Exposure is limited to the test runner on developer and CI machines. |
| vitest, @vitest/mocker | 3.2.7 | CVE-2026-84373, CVE-2026-112949 (moderate) | Fixed only in Vitest 4.1.11 / 4.1.12 (major upgrade). Test-time only. |
| sharp | 0.34.5 | GHSA-f88m-g3jw-g9cj, GHSA-rgj7-g3m4-5g8c, GHSA-wq5f-xc86-pv6w (high, bundled libvips, libheif and librsvg) | The fix is in sharp 0.35.x. For a 0.x package a minor bump is a breaking change, so it was left out. sharp is an optional dependency of Next.js used by image optimization on self-hosted servers. Next.js 15.5.28 accepts `^0.35.5`, so maintainers can opt in with a `sharp` override after testing image routes. |

## What users and forks should do

- Python: recreate the virtualenv or run `pip install -r requirements-lock.txt` again, then `pip install -e . --no-deps`.
- Web: in `apps/web`, run `pnpm install --frozen-lockfile` and rebuild (`pnpm build`), then redeploy. Self-hosted deployments should redeploy promptly because of the Next.js RCE and middleware bypass fixes.
- Do not start the Vitest UI server (`vitest --ui`) on a shared or exposed network until Vitest is upgraded to a release that fixes the remaining advisories.
- Use Node.js 22.23.4 or later in your own CI and hosting.
- Forks that pin their own lockfiles should apply the same version bumps.
