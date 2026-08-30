# Graphify install containment probe (do-not.md item 8)

Date: 2026-08-30

> ## ✅ ARCHITECT NOTE — resolved; this report's final verdict is CORRECT
>
> **Status: an earlier revision of this report was internally contradictory and
> recommended weakening a correct safety rule. The lane has since revised it,
> and the current verdict matrix is right. This block is kept as the audit
> trail, not as a live warning.**
>
> The retracted claim was that `graphify <platform> install` no longer exists.
> It does. Measured directly by the architect on 2026-08-30, three independent
> ways:
>
> - `uv run --project python graphify --help` (0.9.42) line **131**:
>   `codex install    write graphify section to AGENTS.md (Codex)`
> - `graphify --help` (0.9.53, PATH binary) line **144**: the same entry
> - live dispatch: `graphify codex` prints
>   `Usage: graphify codex [install|uninstall]`
>
> So `do-not.md` item 8's warning about `graphify codex install` writing into
> `AGENTS.md` is **corroborated by the tool's own help** and **stays**.
>
> The error's origin is worth recording, because it was the architect's: the
> first probe of the CLI surface read `graphify --help | head -40` against a
> **161-line** help, and the platform subcommands begin at line 120. That
> truncated read was passed to this lane as a premise. It is the display-bound
> failure `.claude/rules/probes-need-a-control-arm.md` rule 3 names explicitly.
>
> **The lane then measured the subcommand form properly, and the decisive
> number is architect-verified:** `graphify codex install` appends **+1,130
> bytes** to the invoking directory's `AGENTS.md`, unconditionally, with no
> `--project` escape. This repo's root `AGENTS.md` is **11,831 bytes** against
> agnix AGM-003's **12,000**-byte cap (measured: `wc -c < AGENTS.md`). So a
> `codex install` here would land at **12,961 — 961 bytes over**, breaking the
> gate. It is not viable in this repository at either version, and that is a
> hard blocker rather than a preference. There is also **no `agents install`
> subcommand at all** — the `agents` platform is reachable only through the
> safe `install --platform agents` form.
>
> **What in this report DOES stand** (measured, with before/after hashes, and
> not affected by the above):
>
> - `graphify install --project --platform {claude,agents,codex}` writes only
>   inside the target project — zero home-directory diff across all six
>   platform × version runs. `--project` is genuine containment.
> - `graphify install --platform …` and `graphify <platform> install` are
>   **different commands with different behaviour**. The probe tested the
>   former; `do-not.md` warns about the latter. They share a word, not a
>   behaviour — which is precisely how the wrong verdict was reached.
> - **0.9.42 silently overwrites a hand-edited `SKILL.md` with no backup;
>   0.9.53 writes `SKILL.md.bak` first.** This repo's pin is the destructive
>   one. Load-bearing for any future skill refresh.
> - The unflagged (no `--project`) form was deliberately never tested against a
>   real home directory, and remains unverified-but-plausible at both versions.
>
> Per `.claude/rules/agent-report-persistence.md`, the lane's text below is left
> verbatim rather than trimmed; this block annotates it.

## ⚠️ Two binaries, two versions — this matters and is reported explicitly

There are **two graphify installations on this machine**:

1. **uv-pinned (this repo's own dependency)**: `graphifyy[all]==0.9.42` at
   `python/pyproject.toml:9`, invoked as
   `uv run --project /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python graphify ...`.
   This is what this repo's `dotfiles_setup.graphify` code runs against.
2. **PATH (what a human or a hook actually invokes typing `graphify`)**:
   version **0.9.53**, resolved from
   `~/.local/share/mise/installs/pipx-graphifyy/0.9.53/bin/graphify` via the
   user-global mise config at `~/.config/mise/config.toml:288`
   (`"pipx:graphifyy" = { version = "0.9.53", extras = ["all"], minimum_release_age = "0s" }`).

Measured directly, both arms, before any install ran:

```
$ which -a graphify
/Users/rmanaloto/.local/share/mise/installs/pipx-graphifyy/0.9.53/bin/graphify
/Users/rmanaloto/.local/share/mise/shims/graphify
$ graphify --version
graphify 0.9.53
$ uv run --project /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python graphify --version
graphify 0.9.42
```

**Every command below states which binary produced it.** This report was
initially written testing only the uv-pinned 0.9.42; that first pass is
retained below and supplemented with a second, separate pass against the PATH
0.9.53, run the same way (throwaway dir outside the repo, `--project`, same
before/after snapshots). The two are never merged into one verdict.

`graphify install --help` at 0.9.42 (identical surface confirmed at 0.9.53 —
same usage line, same platform list, verified by both `install1` runs below):

```
Usage: graphify install [--project] [--strict] [--platform P|P]
Platforms: claude, codex, opencode, kilo, aider, copilot, claw, droid, trae,
  trae-cn, hermes, kiro, pi, codebuddy, antigravity, antigravity-windows,
  windows, kimi, amp, agents, devin, gemini, cursor
```

## ⚠️ CORRECTION — an earlier draft of this report wrongly claimed the
## `<platform> install` subcommand does not exist. It does. See below.

An earlier pass of this probe read only the top ~40 lines of `graphify
--help` and concluded `graphify install --platform P` was the only surface,
so `graphify codex install` (the literal form `do-not.md` item 8 names) must
be retired. **That was wrong** — the help is 161 lines at 0.9.42 (174 at
0.9.53) and the full listing has BOTH forms, confirmed by reading the
complete output at both versions (`grep -n install` on the full text,
matched line-for-line between 0.9.42 and 0.9.53 except for line-number
offsets from an extra platform section at 0.9.53's later lines):

```
line   4:  install [--platform P]  copy skill to platform config dir (claude|...|codex|...|agents|...)
line 120:  hook install             install post-commit/post-checkout git hooks (all platforms)
line 127:  claude install           write graphify section to CLAUDE.md + PreToolUse hook (Claude Code)
line 131:  codex install            write graphify section to AGENTS.md (Codex)
line 133:  opencode install         write graphify section to AGENTS.md + tool.execute.before plugin
line 143:  claw install             write graphify section to AGENTS.md (OpenClaw)
line 145:  droid install            write graphify section to AGENTS.md (Factory Droid)
...  (aider, trae, trae-cn, kilo, copilot, vscode, gemini, cursor, antigravity,
      hermes, kiro, pi, devin all have their own `<platform> install` line)
```

**These are two genuinely different commands, not two names for one
behavior:**

- **`graphify install --platform <p>`** — the generic form tested in the
  first pass below. Copies a skill tree into `.<platform>/skills/graphify/`
  (or `.claude/skills/graphify/` etc) inside the current working directory.
  This is the safe, project-scoped form.
- **`graphify <platform> install`** — a per-platform subcommand that
  **writes directly into that platform's config file** — `CLAUDE.md` for
  `claude`, `AGENTS.md` for `codex`/`opencode`/`claw`/`droid`/`aider`/`trae`/
  `trae-cn`, `GEMINI.md` for `gemini`, etc. **This is the dangerous form
  `do-not.md` item 8 warns about, and it is real, present, and unchanged in
  behavior at both installed versions.** There is no `agents install`
  subcommand — `agents` exists only as an `install --platform` value, not as
  its own per-platform subcommand (confirmed absent from the full listing at
  both versions).

**`graphify codex install` / `graphify claude install` were NOT run against
this repository** — only inside disposable throwaway directories, per the
brief's explicit prohibition. See "Subcommand-form probe" below for the
measured behavior and byte deltas.

## Method

All runs used `--project` inside a throwaway git repo created OUTSIDE this
repository:
`/private/tmp/claude-501/.../scratchpad/graphify-probe-1788118333/`
(git-initialized, with stub `README.md`, `AGENTS.md`, `CLAUDE.md`).

Per the brief, the un-flagged (no `--project`) form was **not run** — running
it against a real home directory is exactly the risk the rule exists to avoid,
so that arm is not measured here.

Blast-radius snapshots were taken before and after each run, covering:
candidate target files (`~/.claude/CLAUDE.md`, `~/AGENTS.md`, `~/CLAUDE.md`,
`~/.agents/AGENTS.md`, `~/.codex/AGENTS.md`, `~/.codex/CLAUDE.md` — sha256 +
size + mtime), top-level listings of `~/.claude`, `~/.codex`, `~/.agents`
(`find -maxdepth 1`), and skills-dir contents (`~/.claude/skills`,
`~/.agents/skills`, `~/.codex/skills`, `find -maxdepth 3`).

Baseline facts worth recording: `~/.claude/skills` does **not exist** on this
host (clean canary for a claude-platform write). `~/.claude/CLAUDE.md` also
does not exist. `~/.codex/AGENTS.md` exists but is 0 bytes
(sha256 `e3b0c442...`, mtime Jul 16). `~/.codex` itself is Codex CLI's large
state directory (~2,256 entries at maxdepth 2) — real user data, not something
this probe touches recursively; only its top-level listing and the two
candidate files inside it were diffed.

## Run 1 — `graphify install --project --platform claude`

Output (verbatim):

```
  references       ->  .claude/skills/graphify/references
  skill installed  ->  .claude/skills/graphify/SKILL.md
  CLAUDE.md        ->  created at .claude/CLAUDE.md

Project-scoped install. Add to version control:
  git add .claude/

Done. Open your AI coding assistant and type:

  /graphify .
...
graphify section written to <throwaway>/CLAUDE.md
  .claude/settings.json  ->  PreToolUse hooks registered (Bash|Grep search + Read/Glob)
...
Project-scoped install. Add to version control:
  git add .claude/ CLAUDE.md
RC=0
```

Files created, all inside the throwaway project root:

- `<throwaway>/CLAUDE.md` (790 bytes) — a fresh file since the stub was
  17 bytes and became 790 after install (root `CLAUDE.md` here is the
  *project's* root, not home — the throwaway repo has no `.claude/CLAUDE.md`
  concept collision; this is expected top-of-repo placement, analogous to
  this dotfiles repo's own root `CLAUDE.md` stub pattern).
- `<throwaway>/.claude/CLAUDE.md` (226 bytes) — the actual graphify section,
  quoted in full below.
- `<throwaway>/.claude/settings.json` (547 bytes) — PreToolUse hooks for
  `Bash|Grep` and `Read|Glob`, pointing at
  `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/bin/graphify
  hook-guard {search,read}` (this repo's own venv binary — a byproduct of
  invoking via `uv run --project .../dotfiles/python`, not something to read
  into "escapes the throwaway dir": it is a *reference* to an existing binary,
  no bytes were written there).
- `<throwaway>/.claude/skills/graphify/SKILL.md` (41,276 bytes)
- `<throwaway>/.claude/skills/graphify/.graphify_version` (6 bytes)
- `<throwaway>/.claude/skills/graphify/references/{transcribe,github-and-merge,
  query,exports,extraction-spec,update,hooks,add-watch}.md` (7 files, 1.2 KB
  – 13.4 KB each; these carry an mtime of Aug 13 — copied from a packaged
  template, not freshly written)

`.claude/CLAUDE.md` content (verbatim, 226 bytes):

```markdown
## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
```

**Home-directory diff after Run 1: zero.** `diff` against the pre-run snapshot
for candidate files, top-level listings, and skills dirs all returned empty
(`NO DIFF` printed for all three checks). `~/.claude/CLAUDE.md` stayed
ABSENT; `~/.claude/skills` stayed ABSENT; `~/.codex/AGENTS.md` unchanged at
sha256 `e3b0c442...`.

**Comparison to this repo's tracked `.claude/skills/graphify/`:** the
`--project --platform claude` install produces exactly the shape this repo
already tracks — `SKILL.md`, `.graphify_version`, and a `references/` tree
with the same 8 filenames observed above (`transcribe.md`,
`github-and-merge.md`, `query.md`, `exports.md`, `extraction-spec.md`,
`update.md`, `hooks.md`, `add-watch.md`). No structural difference found.

## Run 2 — `graphify install --project --platform agents`

Output (verbatim):

```
  references       ->  .agents/skills/graphify/references
  skill installed  ->  .agents/skills/graphify/SKILL.md

Project-scoped install. Add to version control:
  git add .agents/
RC=0
```

Files created, all inside the throwaway project root:

- `<throwaway>/.agents/skills/graphify/SKILL.md` (41,000 bytes)
- `<throwaway>/.agents/skills/graphify/.graphify_version` (6 bytes)
- `<throwaway>/.agents/skills/graphify/references/*.md` — same 8 filenames as
  the claude platform, near-identical sizes (one, `hooks.md`, differs by
  3 bytes: 1270 vs 1267 — platform-specific wording, not a probe artifact)

Notably, **no** `AGENTS.md`/`CLAUDE.md` append and **no** hooks registration
happened for this platform — the tool only wrote the skill tree. (Contrast
with `claude`, which additionally wrote `.claude/CLAUDE.md` and
`.claude/settings.json` hooks, and with `codex` below, which writes both an
`AGENTS.md` section and a hooks file.) This shows `agents` is a genuinely
different, more minimal platform profile, not an alias of `codex` despite the
overlapping name.

**Home-directory diff after Run 2:** `candidate_files.txt` and
`skills_dirs.txt` both diffed clean (`NO DIFF`) against the post-Run-1
snapshot. `toplevel.txt` showed four lines differing, all **mtime-only**
changes to files unrelated to graphify —
`~/.claude/backups` (a directory mtime bump), and three Codex CLI runtime
files (`~/.codex/thread_history_1.sqlite-wal`, `~/.codex/models_cache.json`,
`~/.codex/state_5.sqlite-wal`). This is background noise from other agents
running concurrently in this same multi-agent session (this machine has
several other Codex/Claude agents active), not an effect of the probe: no
file changed size, no file changed content-identifying hash, and no new
top-level name appeared (confirmed by diffing the sorted name list alone,
which was empty).

## Run 3 — `graphify install --project --platform codex`

Output (verbatim):

```
  references       ->  .codex/skills/graphify/references
  skill installed  ->  .codex/skills/graphify/SKILL.md
graphify section written to <throwaway>/AGENTS.md
  .codex/hooks.json  ->  PreToolUse hook registered (.../graphify hook-check -
  intentional no-op; Codex Desktop rejects additionalContext on PreToolUse,
  so graph guidance comes from AGENTS.md)

Codex will now check the knowledge graph before answering
codebase questions and rebuild it after code changes.

Project-scoped install. Add to version control:
  git add .codex/ AGENTS.md
RC=0
```

Files created/modified, all inside the throwaway project root:

- `<throwaway>/.codex/skills/graphify/SKILL.md` (41,318 bytes)
- `<throwaway>/.codex/skills/graphify/.graphify_version` (6 bytes)
- `<throwaway>/.codex/skills/graphify/references/*.md` — same 8 filenames
  (one content difference worth noting: `extraction-spec.md` is 4,431 bytes
  here vs 7,960 for `claude` — per-platform tailored content, not a
  containment concern)
- `<throwaway>/.codex/hooks.json` (285 bytes, quoted below) — a `PreToolUse`
  hook on `Bash` pointing at this **dotfiles repo's own** venv binary
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/bin/graphify
  hook-check`). This is a path *reference* written into the throwaway
  project's config, not a write to that path — the binary itself was
  untouched (confirmed no candidate/toplevel diff touches
  `dotfiles/python/.venv/`).
- `<throwaway>/AGENTS.md` — REWRITTEN in place (17 → several hundred bytes),
  content quoted below. This is the file `do-not.md` item 8 warns
  `graphify codex install` appends to — here it happened via
  `graphify install --project --platform codex`, and the target was the
  **throwaway project's own root `AGENTS.md`**, never this dotfiles repo's
  `AGENTS.md` and never anything under `$HOME`.

`.codex/hooks.json` (verbatim):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/.venv/bin/graphify hook-check"
          }
        ]
      }
    ]
  }
}
```

`AGENTS.md` (verbatim, after rewrite):

```markdown
# AGENTS.md stub

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
```

**Home-directory diff after Run 3:** `candidate_files.txt` and
`skills_dirs.txt` both `NO DIFF`. The top-level-name-only diff (sorted name
lists for `~/.claude`, `~/.codex`, `~/.agents`) was **empty** — no new or
removed entries anywhere under `$HOME`. `~/.codex/AGENTS.md` (the real Codex
CLI home-dir file, 0 bytes, sha256 `e3b0c442...`) was untouched throughout —
confirmed identical across all four snapshots (00/01 baseline through 04
post-codex).

## Comparison to this repo's tracked skill files

- **claude platform** vs `.claude/skills/graphify/` (tracked in this repo):
  identical shape — `SKILL.md`, `.graphify_version`, `references/` with the
  same 8 filenames. No structural difference found.
- **agents platform** vs `.agents/skills/graphify/SKILL.md` (tracked in this
  repo): same install produces the same tree shape (`SKILL.md`,
  `.graphify_version`, `references/`); this repo's own `.agents/` predates
  this probe and was not touched by it (read-only comparison, per the brief).

## Are `codex` and `agents` aliases, or genuinely different platforms?

**Genuinely different**, not aliases. Evidence:

1. Different target directories: `.codex/skills/...` vs `.agents/skills/...`.
2. `codex` additionally writes `.codex/hooks.json` (a `PreToolUse` hook) and
   rewrites `AGENTS.md`; `agents` writes neither — it only drops the skill
   tree, with **no** `AGENTS.md` touch at all in this run.
3. `codex`'s hook is explicitly commented in its own output as a
   Codex-Desktop-specific workaround ("Codex Desktop rejects
   additionalContext on PreToolUse, so graph guidance comes from AGENTS.md"),
   which is meaningless for a generic `agents` profile.

## Second pass — the PATH binary (0.9.53), same three platforms, `--project`

New throwaway dir (also outside this repo), fresh baseline snapshot taken
immediately before this pass (confirmed identical facts to the first pass:
`~/.claude/CLAUDE.md` ABSENT, `~/.claude/skills` ABSENT, `~/.codex/AGENTS.md`
0 bytes, sha256 `e3b0c442...`). This pass used **name-only** top-level
listings (no mtime) specifically to avoid the false-positive noise seen in
the first pass's Run 2 (unrelated background Codex/Claude activity bumping
mtimes on files this probe doesn't touch).

Command: `graphify install --project --platform <p>` (the bare PATH binary,
0.9.53), run separately for `claude`, `agents`, `codex` in three fresh
subdirectories.

Outputs were **structurally identical** to the 0.9.42 pass for all three
platforms (same "references ->", "skill installed ->", hooks/CLAUDE.md/
AGENTS.md lines, same `rc=0`). Byte-for-byte comparison of the artifacts
between the two versions, same platform:

| Artifact | 0.9.42 vs 0.9.53 |
|---|---|
| `.claude/skills/graphify/SKILL.md` | **identical**, 41,276 bytes both, `diff` empty |
| `.claude/skills/graphify/.graphify_version` | **differs by design** — `0.9.42` vs `0.9.53` (the version stamp itself) |
| `.claude/settings.json` | differs only in the hook `command` string: 0.9.42 embeds the full uv-venv path (`/Users/.../dotfiles/python/.venv/bin/graphify hook-guard search`); 0.9.53 embeds the bare `graphify hook-guard search`. This is `sys.argv[0]`/invocation-path self-reference, not a behavior change — each install records the path of the binary that ran it. |
| `.codex/hooks.json` | same pattern: `.../python/.venv/bin/graphify hook-check` (0.9.42) vs bare `graphify hook-check` (0.9.53) |
| `.agents/skills/graphify/SKILL.md`, `.codex/skills/graphify/SKILL.md` | identical bytes to their 0.9.42 counterparts (41,000 and 41,318 bytes respectively) |
| `.claude/CLAUDE.md`, `AGENTS.md` (codex) content | identical, `diff` empty |

**Home-directory diff after all three 0.9.53 runs:** the sha256-keyed
candidate-file check (`~/.claude/CLAUDE.md`, `~/AGENTS.md`, `~/CLAUDE.md`,
`~/.agents/AGENTS.md`, `~/.codex/AGENTS.md`, `~/.codex/CLAUDE.md`) came back
**identical** to baseline for all three platforms. The name-only top-level
listing showed exactly two real (non-graphify) changes across all three
runs: `~/.codex/logs_2.sqlite-shm` and `~/.codex/logs_2.sqlite-wal`
disappeared (a normal SQLite WAL checkpoint from Codex CLI's own background
activity — this machine has other agents running concurrently — not
something `graphify install` writes to or reads), and the `~/.codex`
directory's own size/mtime moved as a byproduct of that. Neither is caused by
graphify: `graphify install --project` never targets `~/.codex/*.sqlite*`,
and the same two files are absent from every artifact list above.
**`--project` is confirmed equally sufficient containment at 0.9.53** for
`claude`, `agents`, and `codex`.

### So: do the two versions differ in what they write, or where?

**No — for the flagged (`--project`) form, 0.9.42 and 0.9.53 write to
identical paths with byte-identical skill content.** The only differences are
the version stamp (by design) and the self-referential hook command path
(which binary ran the install), neither a containment-relevant difference.
**0.9.53 does NOT write anywhere 0.9.42 did not.**

## Third pass — does 0.9.53's diverged-SKILL.md backup behaviour actually fire?

Constructed deliberately, one arm per version, both inside the same
throwaway dir (still outside this repo):

1. `install --project --platform claude` (first install).
2. Manually append a line to the installed `.claude/skills/graphify/SKILL.md`
   (`echo "MANUALLY EDITED - DIVERGED CONTENT" >> ...`), confirmed via sha256
   that this changed the file's hash (orig `3e4d30df...` -> edited
   `e31c67df...`).
3. `install --project --platform claude` again (second install, same
   version).

**0.9.42 (uv-pinned) result:** silently overwrites. `rc=0`. Output line reads
`skill installed  ->  .claude/skills/graphify/SKILL.md` with no mention of
the prior divergence. No `.bak` file, no backup of any kind, anywhere.
`find . -iname '*.bak*' -o -iname '*backup*'` after the second install
returned nothing. Final `SKILL.md` sha256 is back to the packaged
`3e4d30df...` — **the manual edit is gone, unrecoverable.**

**0.9.53 (PATH) result:** backs up, then overwrites. `rc=0`. Output
(verbatim):

```
  references       ->  .claude/skills/graphify/references
  previous copy    ->  .claude/skills/graphify/SKILL.md.bak (differed from the packaged skill)
  skill installed  ->  .claude/skills/graphify/SKILL.md
  ...
```

`.claude/skills/graphify/SKILL.md.bak` was created, sha256 `e31c67df...` —
**byte-identical to the diverged edit**, confirmed by direct hash comparison.
The live `SKILL.md` is still overwritten to the packaged
`3e4d30df...` (no prompt, no refusal — it does not preserve the diverged
version as the active file, it preserves a *copy* alongside the reinstalled
packaged one). So the behaviour is: **detect divergence -> write `.bak` ->
overwrite anyway**, not warn-and-stop or refuse.

Both diverge-test home-directory snapshots (post-0.9.42-diverge and
post-0.9.53-diverge, taken together) diffed clean against baseline — the
`.bak` file and the divergence detection are entirely local to the throwaway
project's `.claude/skills/graphify/` tree; nothing under `$HOME` changed.

## Fourth pass — the `<platform> install` SUBCOMMAND form (the dangerous one), throwaway directory only

Ran at **both** versions, for `claude` and `codex` (no `agents` subcommand
exists — confirmed above). Every invocation happened inside a fresh
throwaway subdirectory (a git-init'd project with 17-byte stub `AGENTS.md`
and `CLAUDE.md`), never inside this repository. Each was run **twice** to
test idempotency, then diffed byte-for-byte between the two versions.

### `graphify claude install`

| | 0.9.42 (uv-pinned) | 0.9.53 (PATH) |
|---|---|---|
| `CLAUDE.md` before | 17 bytes (stub) | 17 bytes (stub) |
| `CLAUDE.md` after run 1 | 790 bytes | 790 bytes |
| Byte delta | **+773** | **+773** |
| Run 2 (same dir) | `rc=0`, output: `graphify already configured in <path> (no change)`, byte-identical sha256 | same — `rc=0`, identical sha256 |
| Cross-version content diff | `diff` of the two versions' `CLAUDE.md` is **empty** — byte-identical | |
| Behavior | **Append**: the stub's original `# CLAUDE.md stub` line survives; a `## graphify` section is appended below it (confirmed by reading the file — the append is additive, not a full-file replace) | |
| Also writes | `.claude/settings.json` (PreToolUse hooks) — same as the generic `install --platform claude` form | |

**Verdict: idempotent, version-identical, append-only (not replace/merge in
the destructive sense — it does not touch pre-existing non-graphify
content).**

### `graphify codex install`

| | 0.9.42 (uv-pinned) | 0.9.53 (PATH) |
|---|---|---|
| `AGENTS.md` before | 17 bytes (stub) | 17 bytes (stub) |
| `AGENTS.md` after run 1 | 1,147 bytes | 1,147 bytes |
| Byte delta | **+1,130** | **+1,130** |
| Run 2 (same dir) | `rc=0`, `graphify already configured ... (no change)`, byte-identical sha256 | same |
| Cross-version content diff | `diff` of the two versions' `AGENTS.md` is **empty** — byte-identical | |
| Behavior | **Append**: `# AGENTS.md stub` line survives; a `## graphify` section (longer than the claude one — includes the `/graphify` slash-command line and the "dirty graphify-out/ files are expected" rule) is appended below | |
| Also writes | `.codex/hooks.json` — a `PreToolUse` hook on `Bash` calling `<the running binary's own path> hook-check`. Content identical between versions except this self-referential path (`.../dotfiles/python/.venv/bin/graphify` vs `~/.local/share/mise/installs/pipx-graphifyy/0.9.53/bin/graphify`) | |

**Verdict: idempotent, version-identical, append-only.**

### The decisive number: is `codex install` viable in THIS repo?

**No, not as-is.** This repo's root `AGENTS.md` is currently
**11,831 bytes**, against the hard **12,000-character** cap enforced by
agnix's `AGM-003` check (`.agnix.toml:77` references this cap explicitly —
the file has already been trimmed once to fit under it, per
`.claude/rules/md-size-budgets.md`'s remedy). A `graphify codex install`
append of **+1,130 bytes** measured above would push it to **12,961 bytes**
— **961 bytes over the cap**, which would fail the `mise run lint-docs`
(agnix) gate. `graphify claude install`'s smaller **+773-byte** append to
the (separate, currently-absent) root `CLAUDE.md` is not blocked by this
specific cap, since `CLAUDE.md` at this repo is a byte-exact `@AGENTS.md`
stub gated by a *different* check (`claude_md_import_stub`) that would
almost certainly also reject a graphify-appended `CLAUDE.md` for no longer
being byte-exact to the stub form.

### Home-directory containment, subcommand form

Snapshots taken immediately before the first subcommand run and immediately
after all four subcommand runs (claude×2 versions, codex×2 versions, 2 runs
each = 8 invocations total) show **zero change** to any candidate file
(`~/.claude/CLAUDE.md` stayed ABSENT; `~/.codex/AGENTS.md` sha256 stayed
`e3b0c442...`) and zero change to `~/.claude/skills` or `~/.agents/skills`
(both stayed ABSENT — the subcommand form doesn't touch skill directories at
all, only the platform's own root config file, confirmed by direct
inspection: `graphify claude install` in the throwaway dir wrote only
`.claude/settings.json`, no `.claude/skills/`). The only top-level-name diff
across the run was the same benign `~/.codex/logs_2.sqlite-{shm,wal}`
churn from concurrent Codex CLI background activity seen in earlier passes
— unrelated to graphify, confirmed absent from every artifact list produced
by any of the runs.

**So: `--project` genuinely is irrelevant to what makes `<platform> install`
dangerous.** It was never a home-directory-escape risk in the way the
generic `install --platform` form without `--project` might be (untested,
per the standing safety instruction) — its risk is that it targets **the
current working directory's own root config file**, unconditionally, with
no flag to redirect or suppress it. Running it inside this repository would
write into *this repo's* `AGENTS.md`/`CLAUDE.md`, not `$HOME` — a
project-root mutation, not a home-directory one, and the one the rule's
existing advice ("run any graphify install in a throwaway directory,
never here") already correctly prevents, independent of any `--project`
flag (the subcommand form doesn't even accept one).

## Which version does `do-not.md` item 8's warning describe?

**Neither version's `--project` form exhibits the mutation the rule warns
about** — that arm (`0.9.42` and `0.9.53` both, three platforms each, six
runs total plus two diverge-test runs) left `$HOME` provably untouched every
time. The rule's warning is about the **unflagged** form, which was
deliberately not re-run against a real home directory in either pass (per
the original brief's safety instruction) — so which version, if either, the
unflagged-mutation claim is true of remains **unverified for both 0.9.42 and
0.9.53**. There is no version-dependent answer to report here because the
dangerous arm was not measured at either version; do not read the clean
`--project` results above as evidence either way about the unflagged form.

What IS version-dependent, and worth folding into any update to the rule or
its surrounding docs: **0.9.53 added the diverged-SKILL.md backup behaviour;
0.9.42 has none.** A user on 0.9.42 who has hand-edited a project's installed
`SKILL.md` will silently lose that edit on the next `graphify install`; a
user on 0.9.53 gets a `.bak` copy first. Since the PATH binary (what actually
runs when someone types `graphify`) is 0.9.53, this protection is live for
this machine's normal usage — but this repo's OWN code path
(`uv run --project .../python graphify`) is pinned to 0.9.42, which does
NOT have it. If this repo's own tooling ever reinstalls the skill
programmatically over a hand-edited copy, it will get the silent-overwrite
behaviour, not the backup one — worth flagging as a currency gap per
[[tool-currency-and-native-first]], independent of the do-not.md question.

## Verdict on `do-not.md` item 8 — a matrix, command form × version

**Correction of an earlier draft:** an earlier version of this section
claimed the `graphify codex install` command shape "no longer exists" and
recommended `do-not.md` be relaxed to drop that warning. **That was wrong**
and has been struck (see the correction note near the top of this report).
The subcommand form is real, present, unchanged between versions, and is
exactly as dangerous as the rule says — see the Fourth pass above.

| Command form | 0.9.42 (uv-pinned) | 0.9.53 (PATH/interactive) |
|---|---|---|
| `install --project --platform P` (`claude`/`agents`/`codex`) | **Safe.** Measured: zero home-directory diff across 3 platforms × 2 runs (incl. a divergence-backup test). Writes only inside the cwd's `.{claude,agents,codex}/`. | **Safe, identically.** Same measurement, same result. SKILL.md content byte-identical to 0.9.42; only the `.graphify_version` stamp and the self-referential hook-command path differ. |
| `install` **without** `--project` | **Untested** (deliberately — the exact risk the rule exists to avoid). Rule's `~/.claude` mutation claim is unverified-but-plausible. | **Untested**, same reasoning. Unverified-but-plausible, identically. |
| `<platform> install` (`claude install`, `codex install`, etc — no `--project` flag exists for this form) | **Dangerous, confirmed.** `claude install` appends +773 bytes to the cwd's `CLAUDE.md`; `codex install` appends +1,130 bytes to the cwd's `AGENTS.md`. Both unconditional, idempotent, append-only (preserves prior content) — but there is no flag to redirect the target away from the cwd's own root config file. | **Dangerous, identically.** Byte-for-byte identical output to 0.9.42 (confirmed by `diff`), same +773/+1,130 deltas, same idempotency. |

**So, precisely:**

- `do-not.md` item 8's warning about `graphify codex install` is
  **corroborated, not overstated**, at both versions — it targets the
  invoking directory's `AGENTS.md` unconditionally, no flag suppresses it,
  and running it against this repo's actual root `AGENTS.md`
  (11,831 / 12,000 bytes, agnix `AGM-003`) would push it to 12,961 bytes and
  fail the `mise run lint-docs` gate. The rule's core advice — run any
  platform install in a throwaway directory, never here — is exactly right
  for this command form, at both versions.
- The rule's separate claim about the **unflagged generic `install`** form
  mutating `~/.claude` was **not re-tested at either version** (deliberately
  — re-running it against a real home directory is the risk the rule exists
  to avoid). Treat as unverified-but-plausible for both 0.9.42 and 0.9.53;
  this probe provides no version-specific evidence either way.
- The **flagged generic `install --project --platform P`** form is
  **confirmed safe at both versions** — this is the one piece of the rule
  that was, in its original phrasing, overstated: it reads as covering every
  `graphify install` invocation, when in fact `--project` genuinely
  contains the generic form. The rule's advice not to run any platform
  install inside this repo remains correct regardless, because the
  subcommand form (which has no `--project` escape) is the one that matters
  in practice — a reader who used `--project` believing it made every
  graphify command safe would be wrong the moment they typed
  `graphify codex install` instead of `graphify install --platform codex`.

**Version-specific finding, orthogonal to `do-not.md`:** 0.9.53 (the PATH
binary — what actually runs when a human types `graphify`) backs up a
diverged `SKILL.md` to `SKILL.md.bak` before overwriting it; 0.9.42 (this
repo's pinned dependency) has no such protection and silently discards a
hand-edited `SKILL.md` with no warning and no recovery path. Worth a
currency note per [[tool-currency-and-native-first]], independent of the
do-not.md question — this repo's own tooling reinstalling the skill
programmatically over a hand-edited copy would get the destructive
behaviour, not the protective one, until the pin is bumped.

**Recommendation:** update `do-not.md` item 8 to:

1. Keep the core warning and the throwaway-directory advice exactly as-is
   — it is correct, and this probe corroborates it for the `<platform>
   install` subcommand form at both installed versions.
2. Clarify that the generic `graphify install [--project] [--platform P]`
   form is a **separate, safer** command surface: `--project` is confirmed
   sufficient containment for it, at both 0.9.42 and 0.9.53 (cite this
   report) — so a reader reaching for the generic form with `--project` is
   not at risk, but should not assume that protects the per-platform
   subcommand form too.
3. Name both command shapes explicitly (`install --platform P` vs
   `<platform> install`) so a future reader cannot conflate the safe one
   with the dangerous one, as this report's own earlier draft briefly did.
4. Leave the unflagged-generic-`install` mutation claim as
   unverified-but-plausible for both versions — do not relax it, since it
   was never re-tested against a real home directory at either version.

## GitHub repos touched

_None — this probe used only the two locally installed `graphify` CLI
binaries (0.9.42 pinned in `python/pyproject.toml`; 0.9.53 resolved from
`~/.config/mise/config.toml`'s user-global pipx install) and read no
external repo source._
