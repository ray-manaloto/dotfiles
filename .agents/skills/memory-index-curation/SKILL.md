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
wc -c ~/.claude/projects/<encoded-cwd>/memory/MEMORY.md   # re-measure before/after each edit
```

⚠️ **The index moves while you work on it.** Auto-memory writes concurrently, so
a figure you measured five minutes ago may already be stale. Re-measure
immediately before and after any edit, and treat an unchanged byte count as your
confirmation that nothing landed underneath you.

## Why this exists

An index hook can hold facts its topic file never mentions — issue refs,
shas, sizes — and a trim that reads better destroys them without warning. The
converse also happens: a hook can be STALER than its file (an older sha), and
migrating it down would push the stale fact into the file.

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
   - **Fact is safe in the file, but the HOOK is where you meet it** → the
     checker sees no loss here and it is right: nothing is destroyed. What is
     destroyed is *eager visibility*. For a trap that keeps recurring, that is a
     real loss, because a memory you never open is one you re-learn the hard way.
     Promote it to a `feedback_*` memory of its own and index it in the Feedback
     section — ~150 B of hook, instead of the 400–2,800 B the session entry was
     spending to keep it in view. This is a judgement call and a good one to put
     to the user; it was the only decision in the 2026-08-07 pass that needed a
     ruling.
3. **Re-run** until `rc=0`.
4. **Now shorten — and actually reach the number you were given.** Rewrite each
   fat hook as a one-line pointer. Re-run to confirm still `rc=0`, and re-measure
   with `wc -c` against the target before you stop.

   Verifying is not the deliverable; it is what makes the deliverable safe.
   Keep compressing hooks until `wc -c` clears the target, then say which
   number you hit — margins are often a few dozen bytes, so confirm rather
   than assume.

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
- ⚠️ **`--refs` cannot see the index entry itself.** It reports the memory
  *files* that cite a name; `MEMORY.md` is not one of them, so the index line
  linking the memory you are about to delete is invisible to it. Verified with
  both arms 2026-08-07: `--refs feedback_codex_worktree` reported **1** citing
  file while `MEMORY.md` also linked it and went unreported. So after `--refs`,
  `grep -rn <name> "$(dirname MEMORY.md)"` across the whole memory directory
  — index included — and resolve what the grep adds.

## Reading the budget

The report prints both ceilings as a percentage of cap, names whichever binds
first, and fails if any entry has fallen past it. Read which one it names
rather than assuming the line count: at this index's ~150 bytes/line the 25KB
cap arrives well before line 200.

Practical consequence: pressure is on **prose length per hook**, not entry
count. Tightening fat hooks buys headroom; deleting whole entries buys less
than it looks like it should.

## What the checker will not catch

It compares **distinctive facts** — issue refs (`#244`), commit shas, byte sizes
— across an entry's title *and* hook. Those are the ones you cannot re-derive
from prose. An entry's *reasoning* ("because the base predates
mise-system.toml") is not extractable and is not checked: a clean `rc=0` means
no distinctive fact is lost, **not** that the line is safe to delete unread.
Read what you are trimming.

Most hooks are prose-only, so the extractor finds nothing to check in them and
"no index-only facts" speaks for a small minority of entries. A clean run is a
floor, never a clearance. The redesign this argues for is
**[#476](https://github.com/ray-manaloto/dotfiles/issues/476) — read it before
curating again**, especially before spending agents on this.

### So you will hand-verify — and your own grep needs a control arm

Because `rc=0` is a floor, the real work is checking a hook's claims against its
topic file yourself. The obvious way is to pull the distinctive tokens out of the
hook and grep the file for each. That probe **fails in the direction that costs
you**: it reports *loss* for anything the file merely says differently.

Case and format variants (`LEDGER` vs `ledger`, `9.5k` vs `9,500`, `BRIEF` vs
`in the brief`) are indistinguishable from deletions to an exact substring
match, and prose is full of paraphrase.

So: **match case-insensitively, and read both sides before believing any miss.**
Then arm the probe — run it against a token you know is absent (invent a fresh
nonsense string every time; one you have written down before is now *in* the
corpus) and confirm it reports missing. Report "N checked, 0 missing, control
arm fired" — never a bare "0 missing".

### Where the bytes actually are

Session entries. `project_session_*` hooks are usually the largest share of
the index — one can run to thousands of bytes — and their facts are almost
always already in the linked file, so compressing them to pointers loses
nothing.

Start there. Feedback entries are mostly at their floor already, and the
session-entry precedent is established: sessions before a cutoff get un-indexed
entirely (nothing deleted — `memory-index` still lists them under "Unindexed",
and they open by name).

The classes are narrow on purpose. An earlier prototype cast wider and
over-reported (`25.8GB` vs `25.8 GB`), and a checker that cries wolf gets
ignored — which costs more than the facts it would have caught. One deliberate
recall gap follows from that: a sha must contain both a digit and an `a-f`
letter, so the ~4% of 7-char abbreviated shas that are all-digits are not
extracted. Without the letter test, every `research-20260714-*` slug and GHA run
id read as a commit sha.

## Trigger

On-demand only; no repository hook runs it. Codex itself warns when
`MEMORY.md` nears or passes its 200-line / 25KB read limit — treat that
warning as the trigger.

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
