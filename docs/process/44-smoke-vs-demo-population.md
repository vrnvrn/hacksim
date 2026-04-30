# 44. Spell out demo vs smoke populations in Makefile help and README

## What changed

`make demo` and `make smoke` run different population sizes. The
README and the Makefile help didn't say so. The full demo runs 1
organiser, 3 designers, 8 builders, 3 judges. `make smoke` runs 1
organiser, 3 designers, 4 builders, 3 judges (the smaller builder
count is so the harness fits a CI minute). A panel reading the README
default and then watching make smoke could read the gap as missing
roles.

Files changed:

- `Makefile`: the `help` target gains two extra lines, one under each
  command, naming the exact population for that path.
- `README.md`: the quickstart paragraph below `make demo` gains a
  one-line note: "the default demo population is 1 organiser, 3
  bounty designers, 8 builders, 3 judges (15 AXL nodes peering on
  loopback). `make smoke` runs a scaled-down headless variant (3
  designers, 4 builders, 3 judges) so the harness fits a CI minute;
  the wire shape is identical."

## Why

Self-explanatory commands are worth a sentence of explanation in the
docs. A judge running `make demo`, then running `make smoke`, then
reading the README defaults should not be wondering whether they hit
a config drift. They should see the population on each path called
out in the Makefile help and in the README.

## How to verify

```
make help
```

The block under `make demo` and `make smoke` shows the populations
inline. The README quickstart contains the same numbers in prose
form.

## Gensyn surface used

None.

## Up next

The MCP claim sweep across README, `Faq.tsx`, and SKILL.md.
