# Spec — can the Claude Code native installer target a SYSTEM location, and can mise drive it?

## Objective

An operator ruling (Q18, 2026-09-15) stands: **Claude Code is baked into the
devcontainer image build.** That ruling has one unresolved consequence, and this
research exists to inform the fix — NOT to re-open Q18.

**The consequence.** The devcontainer mounts a persistent volume over the WHOLE
UID-1000 user home (`.devcontainer/devcontainer.json:119`, and `:129`). The
native installer's canonical target is `~/.local/bin/claude` ->
`~/.local/share/claude/versions/<v>`. So anything the image build writes under
that user's home is MASKED at runtime by the volume: CI's bare-image smoke
(`python/src/dotfiles_setup/image.py:1042`, tier 3, `command -v claude`) can pass
against the image while the actual developer user inside the running container
has no Claude at all.

Answer three questions, each with evidence and a control arm.

## Q1 — Can the native installer install to a SYSTEM-LEVEL location?

Is there a supported, documented way to make Anthropic's native installer place
Claude Code somewhere OUTSIDE a per-user home — e.g. `/usr/local/bin`,
`/opt/claude`, or any path the home volume does not mask?

Look for: an install-prefix/target env var or flag; a documented multi-user or
system-wide install mode; a documented "install for all users" path; whether the
installer refuses to run as root, and what it does if it does run as root.

Report for EACH candidate mechanism: does it exist, is it documented by
Anthropic (not inferred), and what breaks if we use it — specifically whether
the **self-update path still works** from a system location, and whether
`claude doctor` flags a system install as unsupported.

If no such mechanism exists, say so plainly and show the negative's control arm
(a documented flag you DID find, proving the probe can see flags at all).

## Q2 — Is there a mise solution to the home-volume mask?

Independently of the installer: does mise offer a mechanism that survives a
volume mounted over the user home? Consider, and verdict each:

- `mise bootstrap dotfiles` / `[dotfiles]`
- `mise bootstrap services` / `[bootstrap.services]`
- `mise oci`
- `mise dot`
- mise's own install root and whether it can be relocated outside the home
- any documented "externally managed tool" or "require binary on PATH" concept

This repo uses `mise bootstrap` 16x and `mise oci` / `mise dot` ZERO times, so
treat the last two as unexplored rather than rejected.

## Q3 — Can the native installer be run FROM mise config files? (THE OPEN ONE)

The operator's words: *"we still have not identified if we can run the native
installer via mise config files."*

Determine precisely what a mise config file CAN do here:

- Can a `[tools]` entry invoke an arbitrary installer script? Which backend, if
  any (`http:`, `aqua:`, `ubi:`, `vfox:`, a custom plugin)?
- Can a mise TASK be the install point, and can it be made to run at image build
  time in a Dockerfile `RUN`? (`.claude/rules/zero-bash-logic.md` requires the
  logic live in `python/`, with the mise task as a thin entrypoint.)
- ⚠️ `[hooks] postinstall` is ALREADY RULED OUT and is not a candidate: mise
  catches hook failures, warns and CONTINUES (`mise/src/hooks.rs:499`, `520-585`),
  so a failed install would not fail `mise install`. Do not re-propose it.
- Does mise's registry key `claude` (NOT `claude-code`) change any of the above?
  Upstream jdx/mise PR #7334 switched its `version_list_url` to `/latest` and
  added an e2e regression, so `mise latest claude` is an upstream-maintained
  query path.

Then answer the combined question: **is there a shape where ONE mise config
declaration installs the native Claude Code at a location the devcontainer home
volume does not mask?** If yes, give the exact declaration. If no, name which of
the three legs fails.

## Constraints

- Read-only. Run no repository gates, write no report file, modify nothing.
- Grep the offline corpus FIRST:
  `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.
  Only fetch live when the corpus misses.
- Every negative finding needs a control arm — a probe of the same shape that
  DOES return a hit. Invent the known-absent token fresh; do not reuse one.
- Distinguish what a vendor DOCUMENTS from what you INFER. Label inferences.
- Do not recommend re-opening Q18. Q18 is settled: bake into the image.

## Deliverable

For each of Q1/Q2/Q3: verdict, evidence with `file:line` or URL, control arm,
and what breaks. Then ONE recommendation for closing the home-volume mask under
Q18, with its cost stated. If the honest answer is "no mechanism exists, the
repair-after-mount step is unavoidable", say that.

## PREMISES (verify before relying on them)

| # | Premise | Where |
|---|---|---|
| P1 | The home volume covers the whole UID-1000 home | `.devcontainer/devcontainer.json:119` |
| P2 | Tier-3 smoke asserts `command -v claude` on the BARE image | `python/src/dotfiles_setup/image.py:1042` |
| P3 | `postinstall` hooks fail OPEN in mise | `mise/src/hooks.rs:499,520-585` |
| P4 | This repo uses `mise oci` and `mise dot` zero times | coordinator-measured |
