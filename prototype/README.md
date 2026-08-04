# PROTOTYPE — agent-team mechanism bets (throwaway)

⚠️ **Throwaway. Do not merge to `main`.** This branch exists as a primary source for the
claims in `RESULTS.md`. The validated *decisions* go into `docs/agent-team.md`; the probe
code stays here.

## The question

`docs/agent-team.md` commits to a mechanism — **role definitions in `.claude/agents/`
orchestrated by a dynamic workflow script**, with delivery enforced by blocking `SubagentStop` /
`TeammateIdle` hooks and cross-session learning carried by the native `memory:` field. Every one
of those is asserted from **documentation**, not from anything we have run.

**Does the harness actually behave that way on this machine, at Claude Code 2.1.221?**

Five claims. Each needs a **control arm** — a probe that has only ever produced one answer is
not evidence (`.claude/rules/probes-need-a-control-arm.md`).

## Deviation from the skill's two branches, stated deliberately

`/prototype` offers **LOGIC** (a TUI over a state machine) or **UI** (route variants). Neither
fits: there is no state model to drive by hand and no interface to look at. The question is
*empirical* — does a documented mechanism do what it says?

So this follows the shared rules of the skill (throwaway, one command, no persistence, no
polish, surface the state, capture on a throwaway branch) with the artifact shape this repo's
previous `/prototype` run produced: **a claims table, each row with both arms and a verdict**
(`prototype/RESULTS.md`, 7 claims, on `prototype/secrets-cli-claims`).

## Run it

```bash
mise run proto-mechanisms
```

Prints every claim, both arms, and the verdict. No persistence: the only state is a marker file
under `/tmp` that the `SubagentStop` probe uses to block exactly once.

## Files

| Path | Purpose |
|---|---|
| `RESULTS.md` | the claims table — **the actual output** |
| `probe_static.py` | the arms that need no agent spend (docs + CLI binary) |
| `stop_gate.py` | the `SubagentStop` hook body: blocks once, then allows |
| `../.claude/agents/proto-stop-blocker.md` | throwaway agent carrying a frontmatter `Stop` hook |
| `../.claude/agents/proto-memory.md` | throwaway agent carrying `memory: project` |

The two `.claude/agents/proto-*.md` files are **throwaway** and must not survive onto `main`.
