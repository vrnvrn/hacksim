# 02. README skeleton in Gensyn voice

## What changed

Added `README.md` with the project pitch, the "What is HackSim" overview, the quickstart that mirrors the AXL quickstart shape (`make build-axl`, `make hooks-install`, `make demo`), a "How HackSim uses AXL" section that lists the five AXL layers we exercise per cross-agent call, sections for builders who want to extend HackSim and for Gensyn judges who want the criterion-to-code mapping, a brief architecture diagram, and a status pointer to the commit log.

## Why

A reader landing on the GitHub page in two minutes needs to understand three things: what HackSim is, that it actually runs on AXL, and how to try it. The README answers all three. It uses Gensyn vocabulary throughout: AXL, mesh, peer, topology, identity, node, skill. Two GitHub links point back at Gensyn's repos so the lineage is visible.

The "For Gensyn" section is the cover letter. It maps each judging criterion to the specific code paths and docs that satisfy it. The "For builders" section is the contract for anyone who wants to extend HackSim, which is part of how we earn the Foundation grant track.

The README references files that do not yet exist (`docs/AGENTS.md`, `docs/ARCHITECTURE.md`, `packages/skills/hacksim-network/`, `make demo`). Those come in later commits. The commit log and process docs are accurate today and the broken links resolve as commits land.

## How to verify

```
cat README.md | head -40
ls docs/process/
```

The first command prints the pitch and the quickstart. The second shows that this commit ships its own process note alongside.

## Gensyn surface used

None directly. The README references `axl/api/handler.go:10-20` and `research_network.py:214-234` as the integration target, but no code in this commit calls AXL.

## Up next

Commit 03 adds the AXL submodule under `third_party/axl`, the build script `scripts/build_axl.sh`, and `make build-axl` becomes a working target. After commit 03 we have a real AXL binary in the tree and can start exercising the HTTP API.
