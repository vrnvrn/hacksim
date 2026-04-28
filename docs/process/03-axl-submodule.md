# 03. AXL submodule and build script

## What changed

- Added `gensyn-ai/axl` as a git submodule at `third_party/axl`. Recorded in `.gitmodules`.
- Added `scripts/build_axl.sh`, which checks for the Go toolchain, prints the version it found, runs `make build` inside the submodule, and verifies the resulting `node` binary is executable.
- The Makefile target `build-axl` invokes the script.

## Why

AXL is a Go binary maintained by Gensyn. Vendoring it as a submodule preserves the full upstream history and lets us pin a known-good revision. Building from source matches AXL's own quickstart (`make build`, `openssl genpkey`, `./node`) so a reviewer who has read the AXL README sees the same shape inside HackSim.

The script does the smallest possible thing on top of the upstream Makefile. It does not rewrite arguments, does not pin a different toolchain, does not patch source. It is a thin wrapper that adds friendly error messages when the Go toolchain is missing.

## How to verify

```
git submodule update --init --recursive
bash scripts/build_axl.sh
```

Expected: prints "using go <version>", runs the upstream `make build` (downloads Go module dependencies once), prints "ok, built third_party/axl/node", and prints the binary's `--help` output.

If Go is not installed, the script exits 1 with "Go toolchain is required". This is the right failure mode; we surface a missing dependency immediately rather than producing a half-built tree.

The `node` binary is gitignored (see `.gitignore` rule `third_party/axl/node`). Only the submodule pointer is in version control.

## Gensyn surface used

The full AXL repository, vendored at `third_party/axl`. Specifically anchored in this commit, the upstream `Makefile`:

```makefile
export GOTOOLCHAIN := go1.25.5
build:
    go build -o node ./cmd/node
```

We invoke it through `make build`. The pin to `go1.25.5` is preserved via Go's automatic toolchain handling; if the local Go is older, Go fetches the pinned toolchain. Verified with Go 1.26.2 on darwin/arm64; the build downloaded the pinned toolchain transparently.

## Up next

Commit 04 introduces the wire protocol module under `packages/protocol/`, with `Envelope` typed dicts and phase-counter constants matching `research_network.py:50-63`. After that, commits 05 and 06 build the urllib AxlClient that talks to the binary we just compiled.
