# Cold review — `7998d0c..1904601` (`fix/agents-skill-mirror-drift`)

Reviewer: cold-reviewer (Opus 5). No description of intent was supplied; the
account below is derived from the code alone.

Commits: `6927839` (generator), `a0e8922` (`references/**` mirroring),
`1904601` (delete the `CLAUDE.md`→`AGENTS.md` rule, fold tmux case into RULES).

STATUS: complete.

## What the diff does (reviewer's own account)

1. Adds `python/src/dotfiles_setup/skills_mirror.py` (407 lines): a generator
   that renders `.agents/skills/<name>/SKILL.md` from
   `.claude/skills/<name>/SKILL.md` by applying an ordered table of literal
   string substitutions (`RULES`), a masking pass for literals that must never
   be rewritten (`PROTECTED`), and a per-skill override table (`PER_FILE`).
   `references/**` files are mirrored byte-for-byte with no rewriting.
   `EXEMPT` (`graphify`) is skipped entirely; `CODEX_ONLY` is documentation.
2. Registers a `skills-mirror` CLI subcommand (`--check` = read-only, exit 1
   on drift; bare = write) and a `mise run skills-mirror` task.
3. Replaces `hk.pkl`'s `session_review_skill_parity` step (a `cmp -s` on one
   skill pair) with `skills_mirror_parity`, a thin wrapper over `--check`.
4. Adds `workflow.skills-mirror-enforcement` to `suites.toml` and
   `tests/test_skills_mirror.py`; regenerates 21 `.agents/skills/*/SKILL.md`.

## Findings

_(populated below)_

### HIGH — `find_drift` is source-driven only, so the gate is blind to every stale, deleted-source, or extra file in `.agents/skills/**`

`python/src/dotfiles_setup/skills_mirror.py:331` (`find_drift`) enumerates work
exclusively from `mirror_paths()`/`reference_paths()`, both of which walk
`.claude/skills/` (`:285`, `:319`). Nothing ever walks `.agents/skills/`. Three
classes of content are therefore invisible to `--check`:

1. a `SKILL.md` whose `.claude` source was deleted (indistinguishable from a
   legitimate `CODEX_ONLY` skill — `CODEX_ONLY` at `:243` is never read by any
   function, only by a test);
2. a `references/**` file removed from the source side;
3. any other file inside a *managed* `.agents/skills/<name>/` directory.

Measured on a `git archive` of `1904601` in the scratchpad (source tree not
touched):

```
baseline drift: []
after orphan .agents/skills/zz-deleted-skill/SKILL.md   -> drift: []   write_mirror: []
after orphan .agents/skills/context7-cli/references/gone.md -> drift: []
after extra  .agents/skills/pr-workflow/NOTES.md         -> drift: []
CONTROL: modified .agents/skills/pr-workflow/SKILL.md    -> drift: ['pr-workflow']
```

The control arm proves the probe discriminates. This contradicts the claim made
in the step's own comment at `hk.pkl:646` ("covers the WHOLE `.agents/skills/**`
tree") and in `python/verification/suites.toml:1433` (the
`workflow.skills-mirror-enforcement` description). It is the same failure mode
the diff is fixing — a mirror file that silently tells a Codex lane the old
thing — merely moved from "never regenerated" to "never noticed once the source
goes away".

### HIGH — `PER_FILE["adversarial-review"]` rewrites a citation of a *rule's* content into a false claim

`python/src/dotfiles_setup/skills_mirror.py:144` maps `session-handoff` ->
`clear-prep` as an unanchored global substring. In `adversarial-review` it
matches exactly once, at `.claude/skills/adversarial-review/SKILL.md:196`:

> `agent-report-persistence.md` rule 5 rides on `session-handoff`'s audit step

The generated mirror (`.agents/skills/adversarial-review/SKILL.md:196`) now
asserts that rule 5 rides on **`clear-prep`'s** audit step. But
`.claude/rules/agent-report-persistence.md` is a single-sourced file the mirror
still cites by its real name, and it contains no `clear-prep` at all
(`grep -rn "clear-prep" .claude/rules/` -> 0 hits; control arm:
`grep -rn "session-handoff" .claude/rules/` -> 1 hit at
`.claude/rules/agent-report-persistence.md:133`). A Codex reader who opens the
cited file finds the opposite of what the mirror told them.

This is the module docstring's own RESPEC-1 argument (do not rewrite a name
into a path/identity that was never real) applied to paths but not to skill
names.

### MEDIUM — the mirror publishes two rival names for the same skill

`.agents/skills/session-handoff/SKILL.md` is generated and still names itself
`session-handoff` (frontmatter `name: session-handoff` at `:2`, `/session-handoff`
at `:204`, `:212`), while `PER_FILE` redirects every *cross-reference* to
`clear-prep` (`.agents/skills/handoff/SKILL.md:24` -> `.agents/skills/clear-prep/SKILL.md`;
`:3`, `:13`, `:23`, `:51`, `:72`, `:81`). A Codex lane reading `.agents/skills/`
sees three entries for one job (`session-handoff`, `clear-prep`, `handoff`) with
the cross-references pointing at only one of them and the mirrored skill telling
the reader to invoke the other. Either `session-handoff` should be `EXEMPT`
(not mirrored) or the `clear-prep` override should be dropped; today it is both.

### MEDIUM — `render()` is not idempotent, and the one file where it fails inverts a factual claim

`render(render(x)) != render(x)` for `session-handoff` (measured across all 33
managed pairs; it is the only one):

```
-  describes the Claude-side convention this inverts).
+  describes the Codex-side convention this inverts).
```

The `PER_FILE` replacement text at
`python/src/dotfiles_setup/skills_mirror.py:169` embeds the literal `Claude`,
which `RULES[2]` (`:128`) rewrites on any second pass — turning a true statement
into a false one. Today `write_mirror` always renders from source so this never
fires in production, but see the test finding below: the test named
`test_regeneration_is_idempotent` does not test this property.

### MEDIUM — `RULES` codifies a command string that exists on neither harness

`(".claude mcp", "Codex mcp")` at `python/src/dotfiles_setup/skills_mirror.py:129`
produces `` `Codex mcp add` `` in 9 code spans across two generated files
(`.agents/skills/mcp2cli/SKILL.md:3,9,23,137,150,161`,
`.agents/skills/mintlify/SKILL.md:252,254,271`). The real Codex command is
lowercase — `mise exec -- codex mcp --help` -> "Manage external MCP servers for
Codex ... Usage: codex mcp [OPTIONS] <COMMAND>". `Codex` is not a command.
`command -v Codex` *does* resolve on this Mac, but only through case-insensitive
HFS+: the on-disk name is lowercase
(`python3 -c "os.listdir(...)"` -> `['codex']` in
`~/.local/share/mise/installs/npm-openai-codex/0.154.0/bin/`). That is
**exactly** the `.Codex/`-vs-`.codex/` trap the module docstring spends 10 lines
rejecting (`:25-30`) — and this diff re-introduces it for the binary name.

These strings pre-date the diff (`git show 7998d0c:.agents/skills/mcp2cli/SKILL.md`
already has them), but the diff *promotes them to a rule*, so the corruption is
now machine-generated and permanent rather than merely uncorrected — the
opposite of what `PROTECTED` does for `oh-my-claudecode` and `code.claude.com`.

### MEDIUM — a test writes to the tracked working tree

`tests/test_skills_mirror.py:194` is

```python
def test_real_tree_regeneration_is_a_no_op() -> None:
    assert skills_mirror.write_mirror(REPO_ROOT) == []
```

`write_mirror` is the *writer*. Whenever the real tree has drift, this test
mutates tracked files under `.agents/skills/**` **before** its assertion fails.
Demonstrated on the scratchpad copy of `1904601` (one-word edit to a `.claude`
source, then `pytest -k real_tree_regeneration`):

```
1 failed ... test_real_tree_regeneration_is_a_no_op   rc=1
mirror md5 before=31beab94… after=956db704…
*** THE TEST MUTATED A TRACKED MIRROR FILE ***
.agents/skills/tmux-extended-keys/SKILL.md:16: # tmux extended keys (edited) ...
```

`mise run test` uses `-x` and `test_real_tree_is_drift_free` (`:188`) is defined
first, so the ordinary path usually stops before the writer — but that is an
ordering accident, not a guard. Any `-k`, `--lf`, single-test, IDE or reordered
run reaches it. The read-only equivalent (`find_drift(REPO_ROOT) == []`) is
already asserted one test earlier, so this test adds no coverage its neighbour
lacks while adding a side effect on tracked files.

### MEDIUM — `PROTECTED` is inert, and the test that covers it cannot fail

Patching `skills_mirror.PROTECTED = ()` and re-running `find_drift` on the real
tree yields `[]` — identical to the unpatched run. No entry in `RULES`
(`python/src/dotfiles_setup/skills_mirror.py:125-135`) can match either
protected literal: `oh-my-claudecode` and `code.claude.com` contain lowercase
`claude`, and the only lowercase-`claude` rules are `claude mcp` and
`claude code` (both require a following space + word that neither literal has).
The module docstring concedes the mechanism at `:99` ("no rule in RULES touches
lowercase 'claude' at all") and then claims the masking is what makes the
corruption "UNPRODUCIBLE (not merely repaired)" at `:98`. It is the *absence of
a rule*, not the mask, doing that work.

Consequently `tests/test_skills_mirror.py:69`
(`test_render_leaves_oh_my_claudecode_intact`) passes with `PROTECTED` deleted
entirely — a check that can only pass
(`.claude/rules/probes-need-a-control-arm.md` rule 2). To be load-bearing it
would have to assert against a rule that *would* corrupt the literal (e.g. add
a lowercase `claude` -> `codex` rule to a fixture RULES and assert the mask
still holds).

Which entries *are* load-bearing (drop-one mutation on the real tree, drift
non-empty = load-bearing):

| dropped | drifted skills |
|---|---|
| `PROTECTED` (all) | *none* — inert |
| `('.claude/skills/', '.agents/skills/')` | 12 |
| `('Claude Code', 'Codex')` | 6 |
| `('Claude', 'Codex')` | 5 |
| `('claude mcp', 'Codex mcp')` | 2 |
| `('claude code', 'Codex')` | 1 |
| each of the 5 `PER_FILE` keys | 1 each |

### MEDIUM — `test_regeneration_is_idempotent` does not test idempotence

`tests/test_skills_mirror.py:90-103` calls `write_mirror` twice on the same
*source* and asserts the second call is a no-op. `write_mirror` renders from
source on every call, so that is determinism plus a text round-trip, not
idempotence. The property the name claims — `render(render(x)) == render(x)` —
is measurably **false** for `session-handoff` (see the finding above), and this
test passes anyway. It would also pass if the `RULES` table were emptied.

### MEDIUM — the only guard against a stale `PER_FILE` override is in pytest, which the advertised gate does not run

`hk.pkl:649` places `skills_mirror_parity` inside `allSteps`, which is spread
into the `pre-commit`, `check` and `fix` hooks. The `test` step is **not** in
`allSteps` — it exists only under `pre-push` (`hk.pkl:782`). So
`mise run lint` (`hk check --all`, the gate this repo's rules make the
pre-commit bar) runs `--check` but never
`test_per_file_patterns_each_match_their_rendered_source_at_least_once`.

That matters because `--check` cannot detect the class at all. Measured: rewording
one source sentence (`It reads both Claude and` -> `It now reads both Claude and`
at `.claude/skills/session-review/SKILL.md:69`) makes
`PER_FILE["session-review"]`'s second override match zero times. `render` then
emits

```
non-Git, or unmatched root is an `INCOMPLETE` review. It now reads both Codex and
Codex native transcripts and retains user messages, …
```

— the "Codex and Codex" corruption `PER_FILE` exists to prevent
(`skills_mirror.py:55-57`) — `--check` reports drift once, and after
`mise run skills-mirror` writes that text, **`--check` is green again** with the
corruption committed.

Two further weaknesses in that pytest guard:

- it *re-implements* `render`'s mask -> RULES -> unmask pipeline inline
  (`tests/test_skills_mirror.py:252-260`) instead of calling a shared helper, so
  a future reordering inside `render` leaves the test asserting against a
  pipeline production no longer uses;
- `if not source_path.is_file(): continue` (`:249-250`) silently skips a
  `PER_FILE` key whose skill was renamed or deleted, so a wholly-dead override
  is never reported;
- it asserts `count >= 1`, which is what allows the unanchored
  `adversarial-review` / `handoff` overrides (1 and 7 matches) through.

### LOW — the mirror tree is not covered by the dead-reference gate

`python/src/dotfiles_setup/doc_refs.py:67-86` (`DOC_PATHSPECS`) scopes
`check-doc-refs` to `AGENTS.md`, `**/AGENTS.md`, `.claude/CLAUDE.md`,
`.claude/rules/*.md` and `.claude/skills/*/SKILL.md`. `.agents/skills/**` is
absent — and its own comment reads "An uncovered file is exactly where the next
stale ref hides."

Control arm for the consequence: at `7998d0c` the tracked mirror cited
`.Codex/rules/probes-need-a-control-arm.md`, `.Codex/agents/adversarial-critic.md`
and ~40 more `.Codex/...` paths. `.Codex/` has **never** been a tracked path
(`git ls-files | grep -c '^\.Codex/'` -> 0; `git log --all --diff-filter=A
--name-only | grep '^\.Codex/'` -> 0 hits), while the control `git ls-files
.codex` returns 10 real files. So dozens of dead paths sat in a merged tree with
lint green. This diff removes those particular instances but leaves the gate
that would have caught them still not covering the tree.

### LOW — `SKILL.md` drift is compared as text, `references/**` as bytes

`find_drift` uses `read_text(encoding="utf-8")` for `SKILL.md`
(`skills_mirror.py:341-346`) and `read_bytes()` for reference files (`:350`).
Universal-newline translation means a CRLF mirror `SKILL.md` compares equal to
an LF render. Measured: rewriting `.agents/skills/pr-workflow/SKILL.md` with
CRLF gives `drift: []` while the bytes differ from what `write_mirror` produces.
No `.gitattributes` exists in this repo to normalise on commit.

### LOW — `reference_paths` mirrors *every* file under `references/`, including editor/OS droppings

`skills_mirror.py:325` is `sorted(p for p in refs_dir.rglob("*") if p.is_file())`
with no extension or ignore filter, and `.DS_Store` is **not** in `.gitignore`
(`grep -n DS_Store .gitignore` -> no match; none exist today). On this macOS
host, a Finder visit to `.claude/skills/context7-cli/references/` makes
`--check` fail, and the prescribed fix (`mise run skills-mirror`) copies a
binary `.DS_Store` into the tracked `.agents/` doc tree, which must then be
committed for the gate to go green.

### LOW — `write_mirror` is neither atomic per file nor all-or-nothing

`skills_mirror.py:373` / `:382` write in place (`write_text` / `write_bytes`,
which truncate first). There is no tempfile-plus-`os.replace`, and no
transaction across the loop: an interruption leaves one truncated tracked file
and a partially regenerated tree. Content is regenerable from `.claude`, so the
blast radius is bounded — but the failure mode is a *corrupt* tracked file, not
a missing one, and `--check` will then report it as ordinary drift with no hint
that a write was interrupted.

### LOW — dangling in-file cross-reference introduced by the rename

`hk.pkl:632` still reads "for the same reason as `session_review_skill_parity`
below" — the step it points at was renamed to `skills_mirror_parity` by this
same diff, so the pointer resolves to nothing
(`grep -n session_review_skill_parity hk.pkl` -> 1 hit, the comment).
`python/src/dotfiles_setup/skills_mirror.py:210` likewise describes
`session_review_skill_parity` as the thing that "already asserted this file must
be BYTE-IDENTICAL", which after this commit is true only of
`tests/test_session_review.py:994`.

### LOW — contract description miscounts the covered pairs

`python/verification/suites.toml:1433` says the old `cmp -s` "covered exactly
one of 33 skill pairs — the other 32 drifted silently". There are 33 `.claude`
skill directories but **32** managed pairs (`graphify` is `EXEMPT`), so the
uncovered count is 31. Measured: `len(mirror_paths(root))` -> 32,
`len(reference_paths(root))` -> 3. The same figure is repeated in the hk
step's comment at `hk.pkl:645`.

### INFO — `CODEX_ONLY` is documentation-only data

`skills_mirror.py:243` is read by no function in the module (verified by the
orphan probe: an invented `.agents/skills/zz-deleted-skill/` behaves identically
to `clear-prep`). Its docstring says it exists "so a test can assert they are
never touched", which is accurate — but it means the generator has no way to
distinguish a legitimate Codex-only skill from an orphan, which is the mechanism
behind the first HIGH finding. Making `find_drift` walk `.agents/skills/` and
treat `set(agents_dirs) - set(claude_dirs) - EXEMPT - CODEX_ONLY` as drift would
close both at once.

### INFO — `hk.pkl:648` claims the wrong precedent

The comment says the step is the "same shape as `bash_logic_budget`", but
`bash_logic_budget` (`hk.pkl:247-250`) carries
`glob = List("scripts/*.sh", ".devcontainer/scripts/*.sh")` and
`skills_mirror_parity` carries none. The globless form is the *safer* choice
here (it runs even when only `.agents/**` changed); it is the comment that is
inaccurate.

### INFO — tests that cannot fail against the current implementation

- `tests/test_skills_mirror.py:106` (`test_generator_never_deletes_an_unmanaged_agents_skill`):
  no deletion code path exists anywhere in the module, so this can only pass. It
  is a forward-looking regression guard, not coverage.
- `tests/test_skills_mirror.py:220` (`test_exempt_and_codex_only_never_appear_in_mirror_paths`):
  the `CODEX_ONLY` half is entailed by `test_codex_only_skills_have_no_claude_source`
  (`:228`) plus `mirror_paths`'s enumeration from `.claude/skills/`; nothing in
  `mirror_paths` consults `CODEX_ONLY`. Only the `EXEMPT` half is load-bearing.
- `tests/test_skills_mirror.py:197` (`test_context7_cli_references_are_covered_verbatim`)
  asserts a whole-repo basename set `{"docs.md","setup.md","skills.md"}` and
  `"context7-cli" in str(source)` for every pair. Adding a `references/` dir to
  any other skill breaks two assertions in an unrelated change.

### INFO — RESPEC-2 leaves a Claude-only file cited to a Codex reader

`.agents/skills/mcp2cli/SKILL.md:39` is now "Globally-wired shorthands (from
`~/CLAUDE.md`)". The module docstring (`skills_mirror.py:76-83`) argues this is
the honest choice because `~/.codex/AGENTS.md` is empty on this machine. Flagged
only so the trade-off is visible: a Codex lane is pointed at a file its harness
does not read, with nothing in the text saying so.

## Verification performed

- `uv run --project python pytest tests/test_skills_mirror.py -q` -> `18 passed`, rc=0.
- `uv run --project python dotfiles-setup skills-mirror --check` -> `skills-mirror OK`, rc=0.
- `mise run token-check -- hk.pkl 'skills_mirror_parity"] {' 'dotfiles-setup skills-mirror --check"'` -> both bind 1x, rc=0.
- `mise run token-check -- mise.toml …` and `… main.py '"skills-mirror",' '"skills-mirror": lambda'` -> all bind 1x, rc=0.
- All mutations were run against `git archive 1904601` extracted into the
  session scratchpad with `PYTHONPATH` shadowing. No file in the repository was
  edited by this review.

## Findings table

| Severity | Claim | Location |
|---|---|---|
| HIGH | `find_drift` never walks `.agents/skills/`, so orphaned mirrors, deleted reference files and extra files are invisible to `--check` | `python/src/dotfiles_setup/skills_mirror.py:331` |
| HIGH | `PER_FILE["adversarial-review"]` rewrites a citation of `agent-report-persistence.md`'s content into a claim that file does not make | `python/src/dotfiles_setup/skills_mirror.py:144` |
| MEDIUM | The mirror publishes both `session-handoff` and `clear-prep` for one job, with cross-refs pointing only at `clear-prep` | `.agents/skills/session-handoff/SKILL.md:2`, `.agents/skills/handoff/SKILL.md:24` |
| MEDIUM | `render()` is not idempotent for `session-handoff`, and the second pass inverts a factual claim | `python/src/dotfiles_setup/skills_mirror.py:169` |
| MEDIUM | `('claude mcp', 'Codex mcp')` generates `Codex mcp add`, a command on no harness (real form is lowercase `codex mcp`) | `python/src/dotfiles_setup/skills_mirror.py:129` |
| MEDIUM | `test_real_tree_regeneration_is_a_no_op` calls the writer against `REPO_ROOT` and mutates tracked files | `tests/test_skills_mirror.py:194` |
| MEDIUM | `PROTECTED` is inert; its test passes with `PROTECTED = ()` | `python/src/dotfiles_setup/skills_mirror.py:103`, `tests/test_skills_mirror.py:69` |
| MEDIUM | `test_regeneration_is_idempotent` tests determinism, not idempotence, and passes on a non-idempotent renderer | `tests/test_skills_mirror.py:90` |
| MEDIUM | The stale-`PER_FILE` guard is pytest-only; `allSteps` has no `test` step, so `mise run lint`/pre-commit cannot catch a silently-degraded mirror | `hk.pkl:649`, `hk.pkl:782`, `tests/test_skills_mirror.py:239` |
| LOW | `.agents/skills/**` is outside `DOC_PATHSPECS`, so a generated dead path is caught nowhere | `python/src/dotfiles_setup/doc_refs.py:67` |
| LOW | `SKILL.md` compared as text (CRLF passes) while references are compared as bytes | `python/src/dotfiles_setup/skills_mirror.py:341` |
| LOW | `reference_paths` mirrors every file under `references/`, incl. non-gitignored `.DS_Store` | `python/src/dotfiles_setup/skills_mirror.py:325` |
| LOW | `write_mirror` is non-atomic per file and has no all-or-nothing semantics | `python/src/dotfiles_setup/skills_mirror.py:373` |
| LOW | Dangling comment pointer to the step this diff renamed away | `hk.pkl:632`, `python/src/dotfiles_setup/skills_mirror.py:210` |
| LOW | Suite description says 32 pairs drifted; the real count is 31 of 32 managed pairs | `python/verification/suites.toml:1433` |
| INFO | `CODEX_ONLY` is read by no function; it is why orphans are undetectable | `python/src/dotfiles_setup/skills_mirror.py:243` |
| INFO | "same shape as `bash_logic_budget`" is inaccurate — that step has a `glob`, this one does not | `hk.pkl:648` |
| INFO | Three tests cannot fail against the current implementation | `tests/test_skills_mirror.py:106`, `:197`, `:220` |
| INFO | RESPEC-2 leaves `~/CLAUDE.md` cited to a Codex reader | `.agents/skills/mcp2cli/SKILL.md:39` |

## What the diff gets right

- Deleting the blind `.claude/` -> `.Codex/` rewrite is correct and evidenced:
  `.Codex/` was never a tracked path in any commit (0 additions across
  `git log --all --diff-filter=A`), while `.codex/` holds exactly the five
  `codex-*.toml` agents plus `.codex/skills/graphify/**` the docstring claims.
- Dropping the `CLAUDE.md` -> `AGENTS.md` rule is supported by the same
  measurement: every one of its firing sites needed an override.
- The `EXEMPT` treatment of `graphify` is genuinely load-bearing and tested in
  both directions (`tests/test_skills_mirror.py:77`, `:170`).
- `references/**` byte-for-byte with no rewriting is the right call for
  `context7-cli/references/setup.md`'s `--claude` flag.
- Every contract token in the new suite binds exactly one site.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repository under review; all diff, source, test and gate evidence.
- [openai/codex](https://github.com/openai/codex) — `mise exec -- codex mcp --help` probed locally (v0.154.0) to establish the real `codex mcp` command spelling.
