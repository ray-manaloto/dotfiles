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
wc -c ~/.claude/projects/<encoded-cwd>/memory/MEMORY.md   # the byte count you can trust
```

⚠️ **Read the byte count from `wc -c`, never from the `mise run` line.** mise
redacts digit runs in task output — a live regression
(`feedback_mise_run_masks_digits`), so the report's own `22,086` may reach you as
`[redacted]2,086`. The report is the right tool for *what a trim would cost*; it
is the wrong one for *how big the file is*.

⚠️ **The index moves while you work on it.** Auto-memory writes concurrently, so
a figure you measured five minutes ago may already be stale. Re-measure
immediately before and after any edit, and treat an unchanged byte count as your
confirmation that nothing landed underneath you.

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

   ⚠️ **Verifying is not the deliverable; it is what makes the deliverable safe.**
   Across four sandboxed eval runs on 2026-08-07 every run cleared its target,
   but the margins were thin — **17,478 / 17,377 / 17,090 / 16,749 B against a
   17,500 B target**, one of them by 22 bytes. A margin that small is not a
   result you should assume; it is one you confirm. When the verification is
   done, keep compressing hooks until `wc -c` clears the target, then say which
   number you hit.

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

⚠️ **Quantify that before you trust a clean run: 152 of 164 hooks (93%) were
prose-only** when this was measured on 2026-08-02, i.e. the extractor found
*nothing to check* in them. So "no index-only facts" was a statement about **12
entries** presented as one about the index. It is a floor, never a clearance.
Widening the extractor to backticked spans and bolded claims would reach 44%;
the remaining 56% is judgment. Numbers, and the redesign they argue for:
**[#476](https://github.com/ray-manaloto/dotfiles/issues/476) — read it before
curating again**, especially if you are about to spend agents on this (the first
run put **52%** of its tokens into its *least* accurate phase).

### So you will hand-verify — and your own grep needs a control arm

Because `rc=0` is a floor, the real work is checking a hook's claims against its
topic file yourself. The obvious way is to pull the distinctive tokens out of the
hook and grep the file for each. That probe **fails in the direction that costs
you**: it reports *loss* for anything the file merely says differently.

Measured on 2026-08-07, checking 16 session hooks: the first pass reported **5
missing facts. All five were false.** Every one was a case or format variant —
`LEDGER` vs `ledger`, `Byte-search` vs `byte-search`, `BRIEF` vs `in the brief`,
`9.5k` vs `9,500`. A paraphrase is indistinguishable from a deletion to an exact
substring match, and prose is full of paraphrase.

So: **match case-insensitively, and read both sides before believing any miss.**
Then arm the probe — run it against a token you know is absent (invent a fresh
nonsense string every time; one you have written down before is now *in* the
corpus) and confirm it reports missing. On the same pass, 77 distinctive tokens
checked, 0 missing, control arm firing correctly — that is a result worth
reporting, and the bare "0 missing" without the arm is not.

### Where the bytes actually are

Session entries. On 2026-08-07 the 17 `project_session_*` hooks were **8,576 B
of 22,086 (~40%)**, one of them 2,836 B on its own — 12.8% of the whole index
for a single line. Compressing them to pointers took the index **22,086 →
17,292 B (88% → 69% of cap)** with nothing lost, because every fact in them was
already in the linked file.

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
