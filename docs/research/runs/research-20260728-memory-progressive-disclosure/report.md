# Design input: progressive disclosure for the auto-memory index

Date: 2026-07-28. Gathered at Ray's request during clear-prep, as the design
input for the **next** task: rework `MEMORY.md` toward lazy loading /
progressive disclosure rather than trimming it flat.

Sources are captured here so the next session does not re-fetch them — the X
article is **paywalled to `WebFetch` (HTTP 402)** and needed the Chrome
extension.

---

## 1. Thariq (@trq212), "The new rules of context engineering for Claude 5 models" (2026-07-24)

<https://x.com/trq212/article/2080710971228918066> — paywalled; read via Chrome.

The headline datum: Anthropic **removed over 80% of Claude Code's system
prompt** for Opus 5 / Fable 5 "with no measurable loss on our coding
evaluations." The framing is *unhobbling* — the old guidance over-constrained a
model that can now use judgement.

Five "then → now" reversals, verbatim headings:

| Then | Now |
|---|---|
| Give Claude rules | Let Claude use judgement |
| Give Claude examples | Design interfaces |
| **Put it all upfront** | **Use progressive disclosure** |
| Repeat yourself | Simple tool descriptions |
| **Memory in CLAUDE.md files** | **Auto-memory** |
| Simple specs | Rich references |

The two rows in bold are the ones this task turns on.

**On progressive disclosure** (the sentence Ray's ask points at):

> A common myth is that you want to make these a central repository for every
> known practice that you might run into, because Claude would not find it
> otherwise. Instead, **consider having a tree of files that can be loaded at
> the right time.**

It applies the same idea to tools: some are **deferred loading**, where "the
agent must search for their full definitions using ToolSearch before using
them. This allows us to have more tools … that don't take up context until
they're needed." Verification and code review were moved *out* of the system
prompt and into skills Claude calls selectively.

**On CLAUDE.md specifically:**

> Keep your CLAUDE.md lightweight and briefly describe what your repo is for,
> but spend most of the tokens on gotchas inside of the codebase. … Avoid
> stating 'the obvious' things Claude should know by looking at your file
> system or your repo.

**On skills:** "For long skills, try and use progressive disclosure as much as
possible — divide it into many files and split them out."

**On memory:** the "then" was users writing to CLAUDE.md via the `#` hotkey;
the "now" is auto-memory, which "Claude now automatically saves." Note this
repo is already on the "now" side — which is precisely why the index has grown
to the point of needing this work.

`/doctor` is named as the tool that "rightsizes" skills and CLAUDE.md files.

### Linked articles (Ray asked for these too)

| link text | URL |
|---|---|
| "context engineering" | <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents> |
| "a tree of files that can be loaded at the right time" | <https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code> |
| "prompt the newest generation of Claude 5 models" | <https://x.com/trq212/status/2073100352921215386> |
| "Fable field guide" | <https://claude.com/blog/a-field-guide-to-claude-fable-finding-your-unknowns> |

**The `dynamic-workflows` link does NOT contain the tree-of-files guidance** —
probed, and it covers saving workflows to `~/.claude/workflows` and shipping
them in a skill, nothing about progressive disclosure or file layout. The
anchor text oversells the destination; the real substance is in the Anthropic
engineering piece below. Recorded so nobody re-reads it hoping for more.

---

## 2. Anthropic, "Effective context engineering for AI agents" — the load-bearing source

<https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>

**Filesystem as memory.** A file-based memory tool lets agents "store and
consult information outside the context window", to "build up knowledge bases
over time, maintain project state across sessions, and reference previous work
without keeping everything in context." It explicitly names Claude Code's
CLAUDE.md as the *pre-loaded* half — "naively dropped into context up front" —
alongside tools for just-in-time retrieval.

**Just-in-time over pre-computed.** Rather than loading everything, keep
**"lightweight identifiers (file paths, stored queries, web links, etc.)"** and
resolve them through tools on demand:

> This mirrors human cognition: we generally don't memorize entire corpuses of
> information, but rather introduce external organization and indexing systems
> like file systems, inboxes, and bookmarks to retrieve relevant information on
> demand.

Stated tradeoff, not glossed: **"runtime exploration is slower than retrieving
pre-computed data."** The article recommends a *hybrid*, not a wholesale flip.

**Layout is signal — this is the direct answer to "subdirectories".**

> file names, folder hierarchies, naming conventions, and timestamps all
> provide important signals

with the worked example that `test_utils.py` in `tests/` implies something
different from the same name in `src/core_logic/`. So a subdirectory is not
just storage; it is metadata the agent reads before opening anything.

**Three techniques for long-horizon work**, and when each fits:

| technique | what it is | fits |
|---|---|---|
| **Compaction** | summarize and reinitiate a new window, preserving "architectural decisions, unresolved bugs, and implementation details while discarding redundant tool outputs" | tasks needing extensive back-and-forth |
| **Structured note-taking** | write notes to memory outside the window, pulled back in later | "iterative development with clear milestones" |
| **Sub-agent architectures** | clean context windows returning "a condensed, distilled summary … (often 1,000-2,000 tokens)" | complex research / parallel exploration |

---

## 3. What this implies for THIS repo (analysis, not yet decided)

Stated as options for the next session, deliberately **not** pre-decided:

1. **`MEMORY.md` is currently the anti-pattern the article names.** It is a
   flat, fully pre-loaded index — "put it all upfront" — at 23,899 / 25,000
   bytes (96%). Every session pays for all 137 entries regardless of task.
2. **The obvious progressive-disclosure shape** is a small always-loaded root
   index of *categories* pointing into `memory/<topic>/` subdirectories, with
   the per-entry lines living in the subdirectory index and loaded only on
   demand. That matches "a tree of files that can be loaded at the right time"
   and "folder hierarchies … provide important signals."
3. **The hard constraint to check first:** the auto-memory loader's actual
   behaviour. `MEMORY.md` is loaded by the harness, not by us — so whether a
   nested index is *reachable* (and by what mechanism: a link Claude follows, a
   skill, a glob) is an empirical question, and **must be probed with a control
   arm before any restructuring**. A design that assumes the loader recurses,
   when it does not, silently makes every migrated memory invisible — the exact
   failure mode `probes-need-a-control-arm.md` exists to catch, and the stakes
   here are the whole memory system.
4. **`/doctor` is named upstream as the rightsizing tool** and is already
   tracked here as issue #281 (wrap `/doctor` host-config auditing as a skill →
   mise task → python library). Worth reading before hand-rolling an analysis.
5. **The eager-rules budget is the same shape and 4x larger** — `md-budget`
   reports ~132,683 bytes / ~33,170 tokens of eager context every session, of
   which `MEMORY.md` is only ~24KB. If progressive disclosure is worth doing
   for memory, the rules corpus is the bigger prize;
   `.claude/rules/md-size-budgets.md` § "Scoping: the trigger test" already
   works out *which* rules can safely be lazy (file-triggered) and which cannot
   (behaviour- and creation-triggered). **That existing analysis is a hard
   constraint on any "just lazy-load the rules" proposal.**

## GitHub repos touched

_None._ All sources are vendor articles (x.com, anthropic.com, claude.com); no
repository source or docs were read to produce this artifact.
