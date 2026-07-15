---
name: memory-index-curation
description: "Use when curating the auto-memory index (MEMORY.md) — trimming a bloated hook, deleting a stale memory, or reacting to a size warning. Shortening a hook silently destroys any fact that lives only there, so the order is verify → migrate/correct → THEN shorten. Run `mise run memory-index` first."
user-invocable: true
---

# Skill: Memory Index Curation

`MEMORY.md` is the auto-memory index at
`$CLAUDE_CONFIG_DIR/projects/<encoded-cwd>/memory/` (default `~/.claude`).
Only its **first 200 lines or first 25KB, whichever comes first**, load at the
start of every conversation. Topic files it links do not load until read on
demand. So the index is capped and must stay short — and **shortening it is the
dangerous part**.

**Never trim, shorten, or delete by hand first. Run the checker first.**

```bash
mise run memory-index                    # audit: budget + what a trim would cost
mise run memory-index -- --refs <name>   # before DELETING a memory
```

## Why this exists (measured, not theorized)

On 2026-07-14 a routine trim of 4 bloated index lines would have destroyed **4
facts that existed ONLY in the index hook** — `#244`, `#186`, `#194`, and the
`8010c61` squash sha. The topic file each hook linked to never mentioned them.
Nothing warns you; the line just reads better afterwards. They were migrated
first, and the trim then verified clean.

The checker's first live run found a 5th: a hook claiming CI went green at
`3adff36` while its topic file said `c2cecd7` — a *later* commit. Same class of
defect, opposite fix.

## The operation

**verify → migrate *or* correct → THEN shorten.** Never reorder these.

1. **Verify.** `mise run memory-index`. `rc=1` means a trim would lose
   something. The report lists each fact, the hook's line, and the file it
   links to.
2. **Resolve each index-only fact — read BOTH sides before deciding.** The
   report describes; it never prescribes, because the right fix depends on
   which side is stale:
   - **Index is right, file is silent** → migrate the fact into the topic file.
   - **File supersedes the index** → correct the hook (the `3adff36` case:
     migrating it down would have pushed an outdated sha into a file that had
     already moved on).
   - **Fact is dead** → drop it deliberately, having looked at it.
3. **Re-run** until `rc=0`.
4. **Now shorten.** Rewrite the hook as a one-line pointer. Re-run to confirm
   still `rc=0`.

## Deleting a memory

Same silent-loss shape by a different route. Before any delete:

```bash
mise run memory-index -- --refs feedback_colima_recommendation
```

- **Repoint or absorb every inbound citation.** A `[[wikilink]]` to a deleted
  memory rots.
- **Re-read the file for live facts, even if it looks archival.**
  `feedback_colima_recommendation` was marked ARCHIVED but still held a live
  fact (OrbStack's AMD64 bugs make it unsuitable *regardless* of the
  DD-vs-Colima call). It was absorbed into `feedback_docker_desktop_runtime`
  before deletion, and the citation in `feedback_base_image_ci_only` repointed.
- **No inbound refs is not a clearance.** The colima file had two.

## Reading the budget

The report prints both ceilings as a percentage of cap, names whichever binds
first, and fails if any entry has fallen past it. **Do not assume it is the line
count** — an earlier assessment asserted "the LINE count is the nearer ceiling"
over its own numbers (60% of lines vs 82% of bytes), which say the opposite. At
~149 bytes/line the 25KB cap arrives around line 168 and the 200-line cap is
never reached.

Practical consequence: pressure is on **prose length per hook**, not entry
count. Tightening fat hooks buys headroom; deleting whole entries buys less
than it looks like it should.

That wrong belief is also the best cautionary tale here. The checker's first
draft enforced only the line cap — the axis that can never fire — while its own
report correctly printed "bytes is the nearer ceiling". It would have gone green
on the one cap it hits. Correcting a claim in prose does not correct the code
written while believing it.

## What the checker will not catch

It compares **distinctive facts** — issue refs (`#244`), commit shas, byte sizes
— across an entry's title *and* hook. Those are the ones you cannot re-derive
from prose. An entry's *reasoning* ("because the base predates
mise-system.toml") is not extractable and is not checked: a clean `rc=0` means
no distinctive fact is lost, **not** that the line is safe to delete unread.
Read what you are trimming.

The classes are narrow on purpose. An earlier prototype cast wider and
over-reported (`25.8GB` vs `25.8 GB`), and a checker that cries wolf gets
ignored — which costs more than the facts it would have caught. One deliberate
recall gap follows from that: a sha must contain both a digit and an `a-f`
letter, so the ~4% of 7-char abbreviated shas that are all-digits are not
extracted. Without the letter test, every `research-20260714-*` slug and GHA run
id read as a commit sha.

## Trigger

On-demand only, by design. No hook wires it yet: whether it belongs on the
existing `SessionEnd` command-audit hook, on a size threshold, or nowhere is a
decision deferred until a few sessions show how the numbers actually move
(Ray, 2026-07-14). Revisit then, with data.

## See also

- `python/src/dotfiles_setup/memory_index.py` — the checker.
- `.claude/rules/mise-tasks-only.md` — why this is a mise task over a one-off.
- `.claude/rules/use-tool-builtins.md` — the hard gate this cleared in writing:
  `claude-md-improver`, `revise-claude-md` and `claude-automation-recommender`
  are all scoped to CLAUDE.md **by their own `find -name "CLAUDE.md"`**, and
  `/memory` is a viewer/toggle, not a curator. No existing tool fits.
- **Do NOT "refactor" the index to `@import`.** `@path` is a CLAUDE.md-loader
  feature; the loader walks `CLAUDE.md` (and its `.local` variant) up from cwd,
  and the memory dir is not on that walk — `@foo.md` there is inert text. Even
  where it
  works the docs are explicit that it "doesn't reduce context, since imported
  files load at launch." Ordinary markdown links are the documented design and
  are already what the index uses.

## GitHub repos touched

- _None._ — the checker reads `~/.claude` locally; the memory-loader behaviour
  above is from Anthropic's hosted docs at `code.claude.com/docs/en/memory.md`,
  not a GitHub-hosted repo.
