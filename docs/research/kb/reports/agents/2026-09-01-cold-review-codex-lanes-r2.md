# Cold review — commit c293c4d (respec round 2)

**Ref:** `c293c4d` (parent `1aca600`), branch `feat/codex-agent-lanes-884`.
**Reviewer:** cold — no statement of intent received; behaviour inferred from the diff.
**Status:** COMPLETE.

## Scope of the diff

15 files, +834/-639. New gate `python/src/dotfiles_setup/codex_agent_parity.py`
(204 lines), CLI entry in `main.py`, hk step `codex_agent_parity` in `hk.pkl`,
mise task `codex-agent-parity`, tests `tests/test_codex_agent_parity.py` (253
lines). Plus: `hk-common.pkl` exclude rewrite (blanket `.codex/**` -> three
enumerated entries), 4 `.claude/agents/codex-*.md` edits, 4
`.codex/agents/codex-*.toml` rewrites, `docs/hk-builtins-audit.md` counter bump.

_(findings appended below as they are settled)_

---

## Findings

### P1 — The corruption check misses a REAL, on-disk instance of the corruption it exists to catch

`python/src/dotfiles_setup/codex_agent_parity.py:75-79` defines
`CORRUPTION_MARKERS = ("Codex Code", ".Codex/", "Codex mcp add")`. The module
docstring (`:15-23`) and `.gitignore:60-69` justify this by citing measured
scores of 5 and 2 on two exported mirrors.

Both numbers reproduce — but **only via `.Codex/`**, and two of the four
exported mirrors score **zero on all three markers while being unambiguously
corrupted**:

```
$ for f in .codex/agents/{adversarial-critic,claude-code-expert,staleness-auditor,dockerfile-reviewer}.toml; do ...
.codex/agents/adversarial-critic.toml  -> markers=2  (Codex Code=0  .Codex/=2  Codex mcp add=0)
.codex/agents/claude-code-expert.toml  -> markers=5  (Codex Code=0  .Codex/=5  Codex mcp add=0)
.codex/agents/staleness-auditor.toml   -> markers=0  (Codex Code=0  .Codex/=0  Codex mcp add=0)
.codex/agents/dockerfile-reviewer.toml -> markers=0  (Codex Code=0  .Codex/=0  Codex mcp add=0)
```

`staleness-auditor.toml` is corrupted — `grep -ci claude` returns **0**, and it
carries the substitution damage in a shape the markers do not cover:

```
124:- **Harness questions are answered offline.** Anything of the form "does Codex
126:  `docs/Codex` — grep it before reaching for the web.
```

(the source prose is `"does Claude do X"` / `docs/claude-code`).

**Replay — the gate returns 0 on it.** A fixture whose toml body is
`staleness-auditor.toml` verbatim, with only `name`/`model_reasoning_effort`
adjusted so the other three checks pass:

```
violations: []
exit code: 0
claude occurrences (any case): 0
```

So: `Codex Code` and `Codex mcp add` have **never been observed in a real
corruption** (0/4 mirrors); only `.Codex/` has. The gate is a symptom sniffer
bound to a string it does not own, which is precisely what
`.claude/rules/probes-need-a-control-arm.md` rule 9 forbids ("assert the
capability, never sniff for a symptom of its absence"). The positive form
would have caught all four mirrors on one line: every hand-authored toml has
5-18 case-insensitive `claude` occurrences; every exported mirror has **0**.

*Residual protection:* all four tracked tomls do contain at least one
`.claude/`, so today's corpus is not structurally un-checkable — but
`codex-advisor.toml` has `Claude Code=0` and `claude mcp add=0`, so it rests on
a single site.

### P2 — The gate's only production entry point is untested in its failing direction

`codex_agent_parity_main` (`codex_agent_parity.py:189-204`) is what the hk step
and the mise task invoke. No test calls it with a violating tree.
`tests/test_codex_agent_parity.py:187` runs the CLI against the clean real repo
and asserts `rc == 0` — a passing arm only.

**Replay (mutation, restored):** replacing the whole body with `return 0`:

```
tests/test_codex_agent_parity.py  -> 18 passed
tests/ (full suite)               -> 2577 passed, 11 deselected
```

`git diff --quiet python/src/dotfiles_setup/codex_agent_parity.py` -> CLEAN after restore.

A regression that makes the CLI (and therefore the hk step) always green is
invisible to the suite. `find_violations` itself is well covered — this is
specifically the seam between it and hk.

### P2 — The `.toml` half the gate polices has no demonstrated consumer in the documented flow

The four `.md` wrappers invoke codex like this
(`.claude/agents/codex-advisor.md:87-91`, same shape in the other three):

```bash
cat .agent/kb/raw/codex-advisor-prompt.md | codex exec \
  --ephemeral --sandbox read-only \
  --model gpt-5.6-sol \
  -c model_reasoning_effort="xhigh" \
  -o .agent/kb/raw/codex-advisor-verdict.md -
```

Nothing selects `.codex/agents/codex-<name>.toml`. `codex exec --help` on the
pinned CLI (`codex-cli 0.151.0`) has **no `--agent` flag** — only `-p/--profile
<CONFIG_PROFILE_V2>`, which names a config profile, not an agent definition.
And a repo-wide search finds no consumer:

```
$ git grep -n "\.codex/agents" -- . | grep -v ^docs/research
.gitignore:58,70,71,72          # ignore rules
hk-common.pkl:68,72,74,82       # the exclude comment
python/src/dotfiles_setup/codex_agent_parity.py:6,15,63   # the gate itself
python/src/dotfiles_setup/main.py:599                     # the gate's --help text
tests/test_codex_agent_parity.py:241                      # the gate's test
```

Consequences:

* The gate's effort check (`codex_agent_parity.py:167-178`) carries the
  rationale *"without it codex resolves the effort from `~/.codex/config.toml`
  and silently runs at medium"*. That rationale is true of the **CLI flag** —
  `.claude/agents/codex-advisor.md:94-98` states it and cites the measurement —
  and has been transplanted onto the toml field, which the documented
  invocation never reads. The stated harm is already prevented by
  `-c model_reasoning_effort="xhigh"` on the command line.
* The pairing check therefore binds a live file (`.md`) to a file whose
  consumer this repo does not name.

**Labelled unverified:** the Codex *Desktop app* plainly does read
`.codex/agents/` (that is where the four exported mirrors come from), so the
tomls may well serve the Desktop/interactive surface. I could not settle that
from the CLI help or the repo, and neither the commit nor the gate says so.

### P2 — "Parity" enforces nothing about the `.claude/agents/*.md` half

`find_violations` (`codex_agent_parity.py:181-186`) reads **zero bytes** of any
`.md`. It checks only that a file with the right name exists.

Replay — a zero-byte `.md` passes:

```
0  EMPTY .md (0 bytes)   -> PASS (rc=0)
```

(from a degenerate-state matrix; every structural case fails correctly —
both dirs absent -> `empty`, either dir absent -> `unpaired`, `.md` as a
directory -> `unpaired`, `.md` renamed off the `codex-` prefix -> `unpaired`,
empty toml -> `name-mismatch` + `effort`.)

So none of the four things **this commit added or relies on** in the `.md`
half is gated:

| Invariant | Where | Enforced by |
|---|---|---|
| `model: haiku` frontmatter | all four `.md:3` | nothing |
| `--model gpt-5.6-sol` in the invocation | e.g. `codex-advisor.md:89` | nothing |
| `-c model_reasoning_effort="xhigh"` | e.g. `codex-advisor.md:90` | nothing |
| "Never substitute your own reasoning for a failed codex call" | `codex-adversarial-critic.md:211`, `codex-advisor.md:143`, `codex-claude-code-expert.md:234`, `codex-staleness-auditor.md:196` | nothing |
| frontmatter `name` == filename stem | all four | nothing |

```
$ grep -rn "gpt-5.6-sol\|model: haiku\|Never substitute your own reasoning" \
    hk.pkl hk-common.pkl python/verification/suites.toml
(no output)
```

`python/verification/suites.toml:2008` independently records that the
md-budget check "is blind to `.claude/agents/*.md` entirely", so no other lane
covers it either.

**What the gate does enforce:** both halves exist per stem; the toml parses;
`name` == stem; `model_reasoning_effort == "xhigh"`; three literal substrings
are absent. **What "parity" does not mean here:** nothing about the `.md`, no
cross-file agreement between the halves (the `.md` frontmatter `name` is never
compared to the toml `name`), no model pin, no tool-list check, no assertion
that the codex-side prose still says what the Claude-side prose promises.

### P3 — `test_hk_can_actually_see_the_tracked_codex_tomls` never asks hk

`tests/test_codex_agent_parity.py:227-241` asserts on strings parsed out of
`hk-common.pkl`. It is a proxy for hk's behaviour, not a measurement of it, so
it stays green if hk's matcher semantics change, if a broader pattern is added
that happens not to start with `.codex/agents/` (e.g. `**/*.toml`), or if the
same exclusion reappears in `hk-image.pkl`.

The real behaviour is fine today — see area 3 below — so this is a naming and
durability gap, not a live defect. `_exclude_entries`'s own control arm
(`:244-252`) is adequate: `.agent/**` is at `hk-common.pkl:90`, *after* the
`.codex/` entries at `:87-89`, so the parser demonstrably reaches the tail.

### P3 — A non-UTF-8 toml crashes instead of reporting `corrupted`

`codex_agent_parity.py:139` does `path.read_text(encoding="utf-8")` outside any
`try`. Replay: `UnicodeDecodeError`. It fails *closed* — `main.py:2348-2350`
catches `Exception`, logs "Unexpected command failure" and exits 1 — but the
docstring's claim to detect content "overwritten with corrupted content"
(`:10-11`) resolves to a traceback for the binary-overwrite case.

### P3 — The description trims dropped distinct triggers, in the class the repo has already been bitten by

All four descriptions were shortened. None was near the 1,536-char silent
truncation cap that `python/verification/suites.toml:2008` records as a pinned
defect:

```
codex-adversarial-critic.md    before=633 after=360
codex-advisor.md               before=566 after=351
codex-claude-code-expert.md    before=672 after=375
codex-staleness-auditor.md     before=607 after=411
```

So this was a context-budget trim, not a truncation fix — but it removed
matcher surface, which is the same failure mode that suites.toml entry pins
(truncation there deleted the *negative* half of a trigger). Triggers dropped:

* `codex-advisor` — "once before declaring a multi-step deliverable done".
* `codex-claude-code-expert` — "agent teams, channels, workflows"; "before
  designing anything that orchestrates agents".
* `codex-adversarial-critic` — "process change"; "design pass".
* `codex-staleness-auditor` — "specs"; the worked list "(a posture reversal, a
  tool swap, a measured refutation, a shipped defect fix)".

### P3 — Stray double blank line left by the section move

`.claude/agents/codex-advisor.md:104-105` — the "Write the verdict to disk"
section was moved to the new "Protocol" block and left two blank lines before
`## Gather what codex cannot reach FIRST` (line 106). No markdown-lint step
sees this file, so nothing will report it:

```
$ hk check --all --plan --json -g '.claude/agents/codex-advisor.md'
steps that see this file: trailing_whitespace, newlines, mixed_line_ending,
fix_smart_quotes, detect_private_key, check_added_large_files,
check_merge_conflict, check_case_conflict, check_symlinks,
check_executables_have_shebangs, byte_order_marker, gitleaks, typos,
editorconfig-checker, no_platform_literals, no_env_dump, betterleaks,
mise_lock_integrity, hk_audit, contract_token_uniqueness, agnix,
md_size_budget, no_global_skill_leakage, codex_agent_parity,
session_review_skill_parity, claude_md_import_stub, claude_agents_md_pairs
```

Cosmetic.

---

## Areas checked with NO findings

### Area 3 — the `hk-common.pkl` exclude rewrite is correct, and measured

`excludePaths` replaced blanket `.codex/**` with `.codex/config.toml`,
`.codex/hooks.json`, `.codex/skills/**` (`hk-common.pkl:87-89`).

Measured exposure, via `hk check --all --plan --json -S typos -g <glob>`:

| glob | fileCount |
|---|---|
| `.codex/**` | **4** |
| `.codex/agents/**` | 4 |
| `.codex/agents/codex-*.toml` | 4 |
| `.codex/agents/adversarial-critic.toml` (exists on disk, untracked) | 0 |
| `.codex/config.toml` (exists on disk, untracked) | 0 |

**Control arm** — the probe can produce a suppressed result on tracked files:
`docs/research/kb/**` has 302 tracked files and selects **0**; `docs/specs/**`
has 20 tracked and selects **0**; `docs/**` selects 73 of 532. So the exclusion
mechanism is live and the `4` is a genuine exposure.

Exactly the four tracked hand-authored tomls are newly visible — nothing else.
Nothing under `.codex/` that should stay excluded is exposed, because
`.gitignore:54` ignores `.codex/*` wholesale and only `!.codex/agents/codex-*.toml`
(`:70-72`) is un-ignored; hk selects from tracked files, so the exported mirrors
and `.codex/config.toml` are invisible regardless. A corollary worth stating:
all three new `excludePaths` entries are currently **inert** — the files they
name are gitignored, and `.codex/skills/` does not exist yet. They are
belt-and-braces for PR #885, not load-bearing today.

**The diff's `!`-negation claim** (`hk-common.pkl:73-75`) I did not
independently reproduce; testing it requires mutating `hk-common.pkl` and
re-running the gate, and the enumerated form the commit shipped is
measurably correct, so the claim is not load-bearing. Labelled **unverified**.

### Area 4 — the `.toml` rewrites are clean of Claude-Code-only mechanics

```
$ for f in .codex/agents/codex-*.toml; do grep -c 'SendMessage' … ; done
codex-adversarial-critic.toml   SendMessage=0 branch_guard=0 Edit-tool=0 codex-exec=0
codex-advisor.toml              SendMessage=0 branch_guard=0 Edit-tool=0 codex-exec=0
codex-claude-code-expert.toml   SendMessage=0 branch_guard=0 Edit-tool=0 codex-exec=0
codex-staleness-auditor.toml    SendMessage=0 branch_guard=0 Edit-tool=0 codex-exec=0
```

Top-level keys are uniform across all four: `description`,
`developer_instructions`, `model_reasoning_effort`, `name`. No `model` key —
the model is pinned CLI-side.

**Refuted candidate finding:** all four `.md` files instruct `SendMessage`
while declaring `tools: Bash, Read, Grep, Glob, Write`, which omits it. Not a
defect — `$CC/agent-teams.md:271`: *"For an in-process teammate, Claude Code
adds `SendMessage` to that list"*, and the instruction is scoped ("Running as a
teammate, send it with `SendMessage`"). ( `$CC` =
`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.)

All four `.md` carry `--model gpt-5.6-sol` and `-c model_reasoning_effort="xhigh"`
(4-5 and 4 occurrences respectively) and the failure-path prohibition verbatim:
*"Never substitute your own reasoning for a failed codex call."*
(`codex-adversarial-critic.md:211`, `codex-advisor.md:143`,
`codex-claude-code-expert.md:234`, `codex-staleness-auditor.md:196`).

Note: the new "persist first / deliver before idle" protocol block was added to
**`codex-advisor.md` only**; the other three do not carry that header. Whether
they need it is a scope question I cannot settle cold — flagging, not claiming.

### Area 6 — `docs/hk-builtins-audit.md` is a faithful regeneration

```
$ cp docs/hk-builtins-audit.md <backup>
$ mise run hk-audit
[hk-audit] $ uv run --project python dotfiles-setup hk-builtins-audit
wrote docs/hk-builtins-audit.md
rc=0
$ git diff --quiet docs/hk-builtins-audit.md   -> IDENTICAL
```

The generator really ran (control arm: my first attempt used the wrong task
name, `mise run hk-builtins-audit`, which exited rc=1 without writing — an
"IDENTICAL" that proved nothing; re-run with `hk-audit`). 66->67 / 38->39 and
the `codex_agent_parity` row are exactly what the generator emits. No drift
rode along.

### Area 2 — the tests are mostly NOT tautological

`tests/test_codex_agent_parity.py` is unusually well armed for this repo:
`test_correct_claude_references_are_not_corruption:56` is a real
can-it-fail-the-other-way arm, `test_the_exclude_parser_is_armed:244` guards
the parser against returning `[]`, and `test_each_corruption_marker_is_detected_on_its_own:90`
covers each marker individually rather than in aggregate. The failure-kind
tests mutate in the regression's real shape rather than renaming.

The two gaps are the P2 (`codex_agent_parity_main` untested in the failing
direction) and the P3 (`test_hk_can_actually_see_the_tracked_codex_tomls` is a
proxy).

One narrower note: `test_the_hk_step_and_mise_task_stay_wired:199` is a
substring check over `hk.pkl`; `'["codex_agent_parity"]'` would also be
satisfied by a comment quoting it. The step is genuinely wired — verified
independently: `hk check --all --plan -S codex_agent_parity` reports
`"status": "included"` with 444 files matched, and `allSteps` is spread into
the `check`, `fix` and `pre-commit` hooks (`hk.pkl:713,725,731`).

---

## Verification hygiene

Everything mutated was restored. Final state:

```
$ git status --porcelain --untracked-files=no
(empty)
```

Untracked files present are report artifacts written by this and concurrent
review agents under `docs/research/kb/reports/agents/`.

## GitHub repos touched

_None._ All evidence is local to this clone plus the offline knowledge-base
doc tree at `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs`.
