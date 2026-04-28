# 11. hacksim-network skill

## What changed

- New skill manifest at `packages/skills/hacksim-network/SKILL.md` declaring the skill name, description, environment requirements (`AXL_API_PORT`, `HACKSIM_ROLE`, `HACKSIM_SIM_ID`), and the slash commands the skill exposes.
- New Python module at `packages/skills/hacksim_network/hacksim_network.py` implementing the commands. `SkillContext.from_env()` reads the three env vars, `cmd_status` returns identity and topology summary, `cmd_recv` drains and decodes the local recv queue, `cmd_post_bounty` (designers and organiser only) and `cmd_submit_project` (builders only) broadcast typed envelopes via the AxlClient fan-out loop.
- `main()` is the CLI entrypoint: `python -m packages.skills.hacksim_network.hacksim_network <cmd>` writes JSON to stdout and returns exit 0/1.
- 13 tests in `packages/skills/hacksim_network/tests/test_skill.py` cover status, recv (empty, decoded, malformed message skipping), post-bounty (success, role gate, missing fields), submit-project (success, role gate, missing fields), main CLI (stdout JSON, stdin payload, error path).

## Why

This is the agent's lego block. Every Claude Code role session in HackSim has this skill installed in its working directory. Slash commands are how the agent reads its inbox and broadcasts results without writing urllib code by hand. The structure mirrors `skills/autoresearch-network/` from Gensyn's autoresearch demo (one SKILL.md plus one Python module), so an AXL hacker who has read that demo will recognise the pattern immediately.

Role gating happens at the skill layer (not the network layer): a builder cannot call `post-bounty`, a designer cannot call `submit-project`. This keeps the wire protocol open while preventing role drift. The check looks at `HACKSIM_ROLE` set by the orchestrator's spawner, which is authoritative because the role process is launched in a controlled environment.

The skill module exports both the command functions (importable from tests and the choreography) and a `main()` for the CLI path, so test coverage is high and the surface stays uniform.

## How to verify

```
.venv/bin/python -m pytest packages/skills/hacksim_network/tests/ -v
```

Expected: 13 tests pass in roughly 7 seconds (slowest fixture is the FakeAxl threaded HTTPServer setup).

Smoke test against a real AXL node:

```
./third_party/axl/node -config third_party/axl/node-config.json &
NODE_PID=$!
AXL_API_PORT=9002 HACKSIM_ROLE=designer HACKSIM_SIM_ID=test \
  .venv/bin/python -m packages.skills.hacksim_network.hacksim_network status | jq .
kill $NODE_PID
```

The status output prints our public key, IPv6, peer count, and queue depths.

## Gensyn surface used

Three AXL endpoints via `AxlClient`:

- `GET /topology` for status reports and broadcast peer enumeration.
- `POST /send` for fan-out broadcast of `bounty.posted` and `project.submitted` envelopes.
- `GET /recv` for inbox draining.

Same surface the autoresearch demo uses. The MCP and A2A surfaces are the next layer (commits 18-20 add judge MCP service and the cross-mesh score call).

## Up next

Commit 12 layers Claude Code session spawning onto the orchestrator's `Spawner`. The spawner gains a `spawn_role` method that creates a working directory, copies the role's CLAUDE.md, links the hacksim-network skill, exports the three required env vars, and starts a Claude Code subprocess pointed at the working directory. After commit 12 the agent harness is complete and commits 13+ start filling in role personas.
