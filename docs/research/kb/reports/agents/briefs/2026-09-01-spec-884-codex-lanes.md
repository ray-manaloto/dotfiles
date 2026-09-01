# SPEC — dotfiles issue #884: four hand-authored codex-backed agent lanes

## 1. Objective

Claude subscription tokens are constrained until they reset on Wednesday. Four
subagents in `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` currently burn
Claude tokens for work that does not depend on being Claude. Create a parallel
roster of **four hand-authored codex-backed agents** whose reasoning happens
inside the `codex` CLI on `gpt-5.6-sol` at `xhigh` effort, leaving the existing
Claude-backed originals untouched and available after the reset.

The failure this prevents: an agent that *appears* to run on codex but silently
resolves its model and effort from `~/.codex/config.toml` — a file this repo
neither owns nor watches — and therefore runs at `medium` effort on whatever
model that file happens to name. Measured this session: a codex invocation
passing no `--model` still printed `model: gpt-5.6-sol` purely by inheritance,
and passing no effort flag printed `reasoning effort: medium`.

Second failure prevented: an advisory lane that silently substitutes its own
in-model reasoning when the `codex` call fails, which would defeat the entire
purpose while looking like success.

## 2. Files

Create these EIGHT files (all new; none exist):

    .claude/agents/codex-advisor.md
    .claude/agents/codex-adversarial-critic.md
    .claude/agents/codex-staleness-auditor.md
    .claude/agents/codex-claude-code-expert.md
    .codex/agents/codex-advisor.toml
    .codex/agents/codex-adversarial-critic.toml
    .codex/agents/codex-staleness-auditor.toml
    .codex/agents/codex-claude-code-expert.toml

Modify these TWO:

    .gitignore          (un-ignore ONLY the new hand-authored codex agents)
    .claude/CLAUDE.md   (point advisor consults at codex-advisor until the reset)

Do NOT modify, and do NOT create `-codex` variants of, these four existing
Claude-backed originals — they must survive intact for the post-reset reversal:

    .claude/agents/adversarial-critic.md
    .claude/agents/claude-code-expert.md
    .claude/agents/staleness-auditor.md
    .claude/agents/dockerfile-reviewer.md

Do NOT touch the four EXISTING `.codex/agents/*.toml` mirrors
(`adversarial-critic.toml`, `claude-code-expert.toml`, `dockerfile-reviewer.toml`,
`staleness-auditor.toml`). They are Codex-app export output, they remain
gitignored, and they are overwritten by that exporter. See constraint C6.

## 3. Interfaces

### The reference implementation — read it first

`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base` already solved this
problem and its solution is the authority for shape. Read BOTH halves of the
pair before writing anything:

    /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.claude/agents/kb-codex-advisor.md   (112 lines)
    /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.codex/agents/kb-codex-advisor.toml

Follow its section structure, its tone, and its safety clauses. Its headings are:
`When you are the right call` / `How you actually reason: shell out to codex` /
`Write the verdict to disk BEFORE you return` / `Ground every answer in the graph
FIRST` / `What you return` / `Hard limits` / `Fallback`.

Also read one sibling for the non-advisor shape, e.g.
`…/knowledge-base/.claude/agents/kb-adversarial-verifier.md`.

### `.claude/agents/*.md` frontmatter

YAML frontmatter, exactly these keys, matching `kb-codex-advisor.md:1-6`:

    ---
    name: <must equal the filename stem>
    description: <one paragraph; see below>
    tools: Bash, Read, Grep, Glob, Write
    color: <a color not already used by the sibling agents>
    ---

`tools` MUST include `Bash` (to call codex) and `Write` (to persist the report
before returning). It MUST NOT include `Edit` or `NotebookEdit` — every one of
these four agents is read-only advisory and never edits what it examines.

The `description` must end with a clause naming this as the codex-backed stand-in
for its Claude original while tokens are constrained, in the style of
`kb-codex-advisor.md`'s closing sentence.

### `.codex/agents/*.toml`

TOML, matching the shape of the KB tomls:

    name = "<same stem>"
    description = "<same description>"
    model_reasoning_effort = "xhigh"
    developer_instructions = """
    <the same body as the .md, minus the YAML frontmatter>
    """

`model_reasoning_effort = "xhigh"` is REQUIRED in all four. Note that all seven
KB tomls declare an effort; three of dotfiles' four existing mirrors do not, and
that silent `medium` downgrade is one of the defects this change closes.

### The codex invocation — the load-bearing detail

Every one of the four `.md` bodies must instruct the agent to shell out with
BOTH flags explicit. Verified against `codex exec --help` on codex-cli 0.151.0
this session:

    cat <prompt-file> | codex exec --ephemeral --sandbox read-only \
      --model gpt-5.6-sol \
      -c model_reasoning_effort="xhigh" \
      -o <verdict-file> -

`--model gpt-5.6-sol` is NOT optional and NOT redundant. Omitting it currently
happens to resolve correctly only because `~/.codex/config.toml:2` names that
model; the banner reports RESOLVED config, so an inherited value and an explicit
one are indistinguishable in the output. Pin it.

Never `--full-auto`. Never a writable sandbox. These are read-only advisory
lanes.

## 4. Constraints and invariants

- **C1 — the four agents and what each replaces.**
  - `codex-advisor` ← stands in for the `fable-orchestrator:fable-advisor`
    plugin agent (Fable 5). This is the operator's primary ask. It is a
    second-opinion advisor consulted at commitment boundaries: before committing
    to an architecture/migration/API shape, when a problem has resisted two
    attempts, and once before declaring a multi-step deliverable done. It
    advises only and never implements. Model its body closely on
    `kb-codex-advisor.md`.
  - `codex-adversarial-critic` ← `.claude/agents/adversarial-critic.md`. Attacks
    a PROPOSAL (a rule, gate, hook, convention, fix list), one at a time, and
    asks whether the proposal would have caught its own motivating defect.
    Reports with `file:line` and replay evidence. Never edits.
  - `codex-staleness-auditor` ← `.claude/agents/staleness-auditor.md`. Audits
    this repo's instruction and reference prose for claims reality has outgrown.
    Every finding carries a `file:line` anchor, the probe that settled it, and
    the control arm proving the probe could have said the other thing. Never
    edits.
  - `codex-claude-code-expert` ← `.claude/agents/claude-code-expert.md`. Answers
    what **Claude Code** actually does on this machine at this version. Read the
    original's body for its evidence-ledger conventions.
  Read each original `.md` before writing its codex counterpart, and preserve
  the original's purpose, evidence discipline, and output contract. You are
  changing WHERE the reasoning happens, not WHAT the agent is for.

- **C2 — never substitute your own reasoning for a failed codex call.** Each
  body must state plainly: if `codex exec` errors, times out, or returns empty,
  say so explicitly in the returned report and stop. Silently backfilling with
  the agent's own in-model reasoning defeats the entire purpose of the lane and
  must be named as forbidden. `kb-codex-advisor.md`'s `Hard limits` section is
  the model for this wording.

- **C3 — persist before returning.** Each body must instruct the agent to
  `Write` its report to a file under `docs/research/kb/reports/agents/` BEFORE
  it returns or sends any message. An advisor lane in the knowledge-base
  transition went idle without reporting and its verdict survived only because
  it had already been persisted. Say so, and give the path convention.

- **C4 — say that the Claude-backed original resumes after the reset.** Both
  halves of every pair must carry a line naming the original agent and saying it
  is the one to use once Claude tokens reset. Do not delete or deprecate the
  originals.

- **C5 — `.gitignore` must un-ignore ONLY the new hand-authored files.** The
  current block is:

        # Codex CLI temporary state
        .codex/*

  Git does not descend into an ignored directory, so a bare
  `!.codex/agents/codex-*.toml` cannot work. The re-include must un-ignore the
  directory first, re-ignore its contents, then re-include only the new files.
  Update the comment to say what is tracked and why. Keep the existing
  `.codex/*` line — other consumers depend on `config.toml` and `hooks.json`
  staying ignored.

  **Merge-conflict warning:** PR #885 is open and armed and edits THIS SAME
  `.codex` block, adding `!.codex/skills/` and `!.codex/skills/**` plus a longer
  comment. Write the new rules so they compose with that hunk rather than
  replacing it — additive lines, and do not reflow or reword #885's surrounding
  comment text.

- **C6 — the four existing `.codex/agents/*.toml` mirrors stay ignored and
  untouched.** They are Codex-app export output, not hand-authored, and the
  exporter corrupts them with a blind `claude`→`Codex` substitution (measured
  this session: `claude-code-expert.toml` 5 hits, `adversarial-critic.toml` 2;
  control arm: all 7 knowledge-base hand-authored tomls score 0 while the same
  probe finds 6 correct `Claude` references in one of them). Editing them is
  wasted work. Add a short comment in `.gitignore` recording that the exported
  mirrors stay ignored while the hand-authored `codex-*` files are tracked, so a
  later reader does not "fix" the asymmetry.

- **C7 — `.claude/CLAUDE.md` is size-gated and import-gated.** The root
  `CLAUDE.md` is locked to byte-exactly `@AGENTS.md` by the
  `claude_md_import_stub` hk step — do NOT touch it. Put the redirect in
  `.claude/CLAUDE.md`, in the existing "Cross-vendor orchestration" section
  which already carries the `fable-orchestrator:` configuration lines. Keep the
  addition to a few lines: the eager instruction corpus is at ~19.7% of a 200k
  window against a 20% threshold, so every byte in this file is scarce. State
  that advisor consults route to `codex-advisor` while tokens are constrained,
  name the date, and say `fable-advisor` resumes after the reset.

- **C8 — house conventions.** Match the prose voice of the existing four
  `.claude/agents/*.md`. Every claim an agent is told to make must carry
  evidence; every probe must carry a control arm (see
  `.claude/rules/probes-need-a-control-arm.md`). No bash logic beyond the thin
  codex invocation itself (`.claude/rules/zero-bash-logic.md`). Do not add any
  new `scripts/*.sh`.

- **C9 — do not invent flags.** `codex exec --help` was captured this session on
  0.151.0. The flags that exist and matter: `-m/--model`, `-c/--config`,
  `-s/--sandbox`, `--ephemeral`, `-o/--output-last-message`, `--json`,
  `-C/--cd`, `--add-dir`, `--ignore-user-config`. If you want any flag not in
  that list, re-probe `codex exec --help` yourself before writing it.

## 5. Verification

Run all four, from the repo root, and capture the output:

    mise run lint-docs
    mise run lint
    uv run --project python pytest tests/ -x -q
    mise run verify

`mise run lint-docs` (agnix) is the one most likely to bite: it validates agent
documentation structure. `mise run lint` enforces the markdown size budgets and
the `claude_md_import_stub` gate.

Additionally, prove the codex invocation you wrote actually works, with its
control arm — do not just assert it:

    # arm 1: the invocation as written in the agent body
    echo 'Reply with exactly: OK' | codex exec --ephemeral --sandbox read-only \
      --model gpt-5.6-sol -c model_reasoning_effort="xhigh" - 2>&1 | grep -E '^(model|reasoning effort):'
    # must print:  model: gpt-5.6-sol   AND   reasoning effort: xhigh

    # arm 2 (control): the same call with the effort flag removed
    echo 'Reply with exactly: OK' | codex exec --ephemeral --sandbox read-only \
      --model gpt-5.6-sol - 2>&1 | grep -E '^reasoning effort:'
    # must print:  reasoning effort: medium

If both arms print the same thing, the flag is decoration and the spec is not
met. Report both arms' actual output.

Also confirm the gitignore rules do what C5 requires:

    git check-ignore -v .codex/agents/codex-advisor.toml          # must print NOTHING (rc=1)
    git check-ignore -v .codex/agents/claude-code-expert.toml     # must still be IGNORED
    git status --short .codex/                                     # must list ONLY the 4 new codex-*.toml

## 6. Commit

COMMIT: lane — commit on the current branch `feat/codex-agent-lanes-884`, scoped
to the files this spec names. Do not push. Do not open a PR. Do not merge, and
do not touch any other branch: PR #885 is armed on `chore/deps-currency-20260831`
and any interference with it is destructive.

## 7. PREMISES

- L1 `.gitignore:54` is `.codex/*`, under the comment `# Codex CLI temporary state`; no negation for `.codex/agents/` exists on `origin/main` — read this session.
- L2 `~/.codex/config.toml:2` is `model = "gpt-5.6-sol"` and `:3` is `model_reasoning_effort = "medium"` — read this session; this is the un-owned file C1's inheritance hazard refers to.
- L3 `.claude/CLAUDE.md:42` is `- fable-orchestrator: implementation lane = codex` and `:43` is `- fable-orchestrator: codex effort = xhigh` — read this session.
- L4 codex-cli version is `0.151.0`; the flag list in C9 was captured from `codex exec --help` this session.
- L5 Control-armed live measurement this session: same call without `-c model_reasoning_effort` printed `reasoning effort: medium`; with it, `xhigh`. The flag bites.
- L6 A live call passing NO `--model` still printed `model: gpt-5.6-sol`, inherited from L2 — the banner reports resolved config, not arguments.
- L7 Only `.codex/agents/adversarial-critic.toml:3` declares `model_reasoning_effort` (value `"high"`); the other three dotfiles mirrors declare none — read this session.
- L8 All four `.claude/agents/*.md` exist with these frontmatter values: adversarial-critic `model: opus` + `effort: high`; claude-code-expert `model: opus`; staleness-auditor `model: opus`; dockerfile-reviewer declares neither — read this session.
- I1 `kb-codex-advisor.md:1-6` frontmatter keys are exactly `name`, `description`, `tools` (`Bash, Read, Grep, Glob, Write`), `color` (`teal`) — read this session.
- I2 `kb-codex-advisor.toml:1-3` keys are `name`, `description`, `model_reasoning_effort = "xhigh"`, followed by `developer_instructions = """…"""` — read this session.
- P1 knowledge-base tracks ALL of `.codex/` (7 agent tomls plus `config.toml` and `hooks.json`; `git ls-files .codex/` read this session) and has no `.codex` gitignore rule. Data-level match: same two-surface Claude/Codex agent-pair layout, same operator, same codex CLI version — so its tracked-and-hand-authored posture transfers directly to the new dotfiles files. It does NOT transfer to dotfiles' four exported mirrors, which knowledge-base has no equivalent of.
- P2 `kb-codex-advisor.toml:46-47` contains `--model gpt-5.6-sol` and `-c model_reasoning_effort="xhigh"` on separate continuation lines — read this session; this is the invocation shape section 3 pins.
- L9 Corruption measurement this session: `grep -c 'Codex Code\|\.Codex/\|Codex mcp add'` scored 5 on dotfiles `.codex/agents/claude-code-expert.toml` and 2 on `adversarial-critic.toml`, versus 0 on all seven knowledge-base tomls; control arm — the same probe found 6 correct `Claude`/`.claude/` references inside `kb-codex-advisor.toml`, so it was capable of matching text there.
- L10 PR #885 is OPEN with auto-merge armed on branch `chore/deps-currency-20260831`, and its diff modifies the `.codex` block of `.gitignore` (adding `!.codex/skills/` and `!.codex/skills/**`) — read from `git diff origin/main...5d8415d8 -- .gitignore` this session.
- A1 ASSUMPTION: agnix (`mise run lint-docs`) accepts new `.claude/agents/*.md` files that follow the existing four's frontmatter shape. Held without a code read because the validator's rule set is large and the verification step exercises it directly — if it rejects them, that is a spec gap to report, not something to work around by weakening the frontmatter.
