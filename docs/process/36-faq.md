# 36. FAQ on the docs page for judges and curious users

## What changed

Adds an FAQ component on `/docs` between the doc cards and the About AXL panel. Native `<details>` accordions, server-rendered, no client JS. Ten questions a Gensyn judge, an ETHGlobal reviewer, or a general user is likely to ask before reading any code.

Questions covered:

- What AI are the agents using? (Claude haiku 4.5, optional, with deterministic stub fallback)
- How does HackSim use Gensyn AXL? (the four AXL surfaces with concrete endpoint names)
- How is HackSim different from Gensyn's autoresearch demo?
- Do I need an Anthropic API key? (no)
- How long does a sim take? (pace presets, with the smoke pace timing called out)
- Are the projects the agents build real, runnable code? (yes, with the `git archive` command shown verbatim)
- Is it safe to render agent-written code in my browser? (CSP and iframe sandbox attributes shown verbatim)
- Is the AXL qualification gate satisfied? (yes, with the proof: separate Go AXL processes per role)
- How do I verify every cross-agent byte goes through AXL? (`tcpdump` and `lsof` commands shown)
- Was this built during the hackathon? (yes, ETHGlobal Open Agents 2026, link to `vrnvrn/hacksim`)

`apps/web/components/Faq.tsx` is the new file (one component, ten entries, light helper components for inline `<code>` and lists). `apps/web/app/docs/page.tsx` mounts it between the existing doc cards and the About AXL panel.

Code snippets are short and concrete. No em dashes, no rhetorical contrast, no co-author trailers. 65 vitest tests pass; build clean.

## Why

A judge who lands on the docs page should be able to answer the qualification questions in under a minute without opening a single source file. The doc cards already point at the right canonical files, but each click is a context switch; an FAQ collapses the most-asked questions into one scroll.

The questions were chosen by simulating a judge read of our repo. Two questions confirm the AXL qualification gate (each role runs its own AXL Go binary; the qualification rule for the bounty), two clarify the LLM story (where the model is called, when it falls back, what happens with no key), one calls out the safety story for arbitrary agent-written code rendered in a browser. The rest are general orientation.

Native `<details>` instead of a Radix Accordion keeps the page server-rendered with zero client JS. The accordion behaviour is fine without animation; the trade-off (no smooth open transition) is worth the simplicity.

## How to verify

```
cd apps/web
bun run test                  # 65 vitest tests pass
bun run build                 # clean
```

Open `http://localhost:3000/docs`. The FAQ sits between the doc cards and the About AXL panel. Each `<details>` opens and closes with a click. The verification snippets (`tcpdump`, `lsof`, `git archive`) are runnable as written.

Targeted writing-rules scan:

```
LC_ALL=C grep -nE '—|not just|Not only|Not just' apps/web/components/Faq.tsx
```

No matches.

## Gensyn surface used

None directly. The FAQ documents the four AXL surfaces the rest of the system uses (`/topology`, `/send`, `/recv`, `/mcp/{peer}/{service}`), but does not call them itself.

## Up next

A reviewer asked whether they could try the system with their own Anthropic key without rebooting `make demo`. Tracked under commit 37, which adds a localhost-gated password input to the Settings popover.
