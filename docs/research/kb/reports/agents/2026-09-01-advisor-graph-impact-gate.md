# Advisor verdict: an unbypassable graph-impact gate on every PR

**Date:** 2026-08-31 · **Lane:** `codex-advisor` (reasoning ran in `codex exec`,
`gpt-5.6-sol`, `model_reasoning_effort=xhigh`, `--sandbox read-only`).
**codex call: SUCCEEDED, rc=0.** Banner confirmed `model: gpt-5.6-sol` /
`reasoning effort: xhigh`. Nothing below is this agent's own substituted
reasoning except the two verification sections explicitly labelled as such.

> **INTENDED TRACKED PATH:**
> `docs/research/kb/reports/agents/2026-09-01-advisor-graph-impact-gate.md`
> The repo write was **DENIED by the PreToolUse `branch_guard`** — the session is
> on `main` (`git branch --show-current` → `main`, checked twice, before and
> after the consult). This file is at the gitignored fallback
> `.agent/kb/raw/codex-advisor-graph-impact-gate.md` and **must be moved onto a
> branch** to survive.

**Raw artifacts:** prompt at
`.agent/kb/raw/codex-advisor-graph-impact-gate-prompt.md`; verbatim codex output
at `.agent/kb/raw/codex-advisor-graph-impact-gate-verdict.md`; run log at
`.agent/kb/raw/codex-advisor-run.log`.

---

## VERDICT (codex, verbatim first line)

> **Overrule hk as the enforcement boundary: do not mandate the current
> `graphify prs` result; first close its coverage gaps, then enforce a trusted
> offline recomputation through a no-bypass GitHub rule, with hk only as the
> local mirror.**

## THE RISK THAT DECIDES IT

Perfect enforcement would currently certify **"no impact" for this repository's
highest-risk changes**. An unbypassable false negative is worse than an advisory
limitation.

Measured (this agent, control-armed): graph coverage is **771 of 983 tracked
files = 78.4%**, but the misses are inverted against risk —

| File | Graph coverage |
|---|---|
| `mise.toml` | NOT COVERED |
| `hk.pkl` | NOT COVERED |
| `.github/workflows/ci.yml` | NOT COVERED |
| `.devcontainer/Dockerfile` | NOT COVERED |
| `mise.lock` | NOT COVERED |
| `python/verification/suites.toml` | NOT COVERED |
| `docker-bake.hcl` | COVERED |
| `python/src/dotfiles_setup/hook_guard.py` | COVERED |
| `renovate.json` | COVERED |

Control arm: the same matcher returned COVERED for three files and NOT COVERED
for six, so it discriminates in both directions. Graph composition: 14,751
nodes / 20,191 edges over 771 distinct `source_file` values — **md=605, py=145**,
sh=11, json=5, lua=1, hcl=1, toml=1.

## THE CORRECTION THAT MATTERS MOST — and it is worse than codex said

codex corrected my E5 (that a CI cold build could repair coverage):
`graphify update` is **incremental over an existing graph**; a cold runner needs
`extract --code-only`, which skips semantic documents.

**This agent then verified that claim directly, and it is stronger than stated.**
In `python/.venv/.../graphify/detect.py:44-45`:

- `CODE_EXTENSIONS` contains **no `.toml`** and **no `.pkl`**.
- `DOC_EXTENSIONS` = `{.md, .mdx, .qmd, .skill, .txt, .rst, .html, .yaml, .yml}`.
- `detect.py:1886-1893` classifies an extensionless file (its own comment names
  **Dockerfile**) as `unclassified`.

Control arm: `.py` and `.md` **are** in those sets, and are exactly the two
best-covered extensions in the real graph (145 / 605).

**Consequence:** `mise.toml`, `hk.pkl`, `suites.toml`, `mise.lock`,
`shared.toml` and the `Dockerfile` are not a coverage *gap that a rebuild
closes* — they are **structurally outside graphify's file-type model**. "Fix
coverage first" therefore requires upstream extension support that does not
exist today. `ci.yml` is a *doc* under this taxonomy, so `--code-only` drops it
too.

## A — hk is the wrong TRUST layer, but a legitimate feedback layer

The existing ban (`.claude/skills/blast-radius/SKILL.md:3` and `:59`,
`mise.toml:773`, `python/src/dotfiles_setup/graphify.py:482`) is correct **about
the entry point, not the computation**. `compute_pr_impact(files, G)`
(`graphify/prs.py:252`) is a pure function of (changed-file list, graph);
`fetch_pr_files` (`prs.py:230`) is merely one way to obtain the list —
`git diff --name-only` is another. So an offline hk linter is *possible* without
violating the no-network rule.

codex's ruling on the two formulations:

- **Artifact-existence gate: unacceptable.** "It proves only that bytes exist."
- **Trusted CI recomputation** from explicit base/head SHAs with a pinned graph
  builder is the correct formulation. Any artifact should be *generated from*
  that result, never *supplied as* the authority.
- hk is fine as developer feedback and for code reuse; it is the wrong trust
  layer because "its local hook is bypassable, and its configuration and checker
  are PR-controlled."

Also note what the metric actually is: `compute_pr_impact` sums nodes whose
`source_file` matches a changed file (`_path_match`, `prs.py:245`). **There is
no dependency traversal.** It is a *graph footprint*, not a blast radius. The
real reverse traversal is a different, offline command — `graphify affected`
(`graphify.py:397`).

## B — with an owner/admin token, NO current layer is unbypassable

| Surface | Concrete bypass |
|---|---|
| Local hk hook | `git commit --no-verify`, another git client, API-created commits, or editing the hook. Git suppresses the hook before it starts (`.claude/rules/do-not.md` #9). |
| PreToolUse guard | Fails open on its own errors; fail-open by design for `sh -c`/`eval`, `$(…)`, base64, aliases (`.claude/rules/mise-tasks-only.md`). Governs only that harness. |
| `mise run ship`/`land` | Direct git/GitHub API or another client avoids them entirely (`python/src/dotfiles_setup/pr.py:573`, `:829`). |
| Actions job via `ci-gate` | Blocks ordinary non-admin credentials **if** the checker and the status identity are trusted. `ci-gate` (`.github/workflows/ci.yml:350-374`) does really aggregate its four upstreams. But a PR-controlled workflow can be weakened, and an admin is exempt from the current classic protection. |

**The `enforce_admins` asymmetry IS the hole it looks like.** Measured today:

- Classic protection on `main`: `required_status_checks.contexts == ["ci-gate"]`,
  `strict: false`, **`enforce_admins.enabled: false`**.
- Ruleset 19868073 "main: require a pull request": `enforcement: active`,
  **`bypass_actors: []`**, `current_user_can_bypass: "never"` — but it contains
  **only a `pull_request` rule, no required-status rule.**

codex's reading: rulesets and branch protection layer together, so the owner
must still open a PR, but `ci-gate` lives only in the admin-exempt classic
protection and does not transfer into the no-bypass ruleset. Therefore **an
owner token must create a PR but can bypass the `ci-gate` requirement**, and can
edit or delete the ruleset. Additionally,
`require_extra_approval_for_unattributed_changes: true` has **no effect** while
`required_approving_review_count` is `0`.

The only layer class that can be genuinely non-bypassable is GitHub-hosted merge
policy that the agent's credential can neither bypass nor administer.

## C — a hand-supplied graph-impact section is security theatre

codex, plainly: "A manually supplied 'graph-impact section' is security theatre.
A content hash alone does not fix that: an agent can fabricate content and hash
the fabrication."

What resists is **independent recomputation by trusted code**, bound to: exact
base/head commit OIDs, the normalized diff, pinned analyzer + graph-builder
identities, and a check result issued by a **dedicated GitHub App whose identity
the ruleset requires** (a required check can be restricted to an expected App
source; otherwise any writer can post a status with that name).

What it still cannot prove: that anyone **understood** the report; that
graphify's model is complete; that a shallow file-footprint metric represents
semantic blast radius. "Calling the resulting attestation 'reviewed blast
radius' would still be theatre."

## D — how to handle graph silence, without an escape hatch

"The premise that this metric is a universal blast radius is wrong. Treat it as a
**graph footprint**." Before it becomes blocking, every changed path needs
exactly one trusted classification:

1. **Graph-covered** → report the computed node/community footprint.
2. **Explicitly unsupported high-risk path** → report `UNMODELED BY GRAPHIFY`
   and require its own specific deterministic gate.
3. **Unknown / unexpectedly uncovered** → **fail closed.**

The unsupported registry and its fallback mapping must live **outside
PR-controlled policy**. Explicitly rejected: broad extension exclusions, a
developer-authored `N/A`, exempting a whole mixed PR because one file is
unsupported. Dependency and lockfile PRs need their dependency-specific
evidence regardless of graphify.

Until that coverage contract exists, graphify output stays **advisory**.

## E — recommended layered design

1. **Meaning and coverage** — define the metric as *graph footprint*; unknown
   coverage fails closed.
2. **Local UX** — an offline hk custom linter previews the exact calculation.
   Useful, never authoritative.
3. **Trusted computation** — a dedicated GitHub App, or a carefully isolated
   base-branch workflow, computes from exact git SHAs without executing
   PR-controlled code. (`pull_request_target` runs in base-branch context but
   GitHub warns against executing untrusted PR code there.)
4. **Host enforcement** — a no-bypass ruleset requires that check and pins its
   expected App source. The AI credential must lack Administration, bypass, and
   status-writing permissions.
5. **Presentation** — the trusted checker publishes the exact-head report as a
   check summary or bot-owned comment. A committed artifact is optional
   evidence, never the gate.

### Carry back to the operator verbatim

> Do not enforce `graphify prs` in hk. Use hk only for local feedback; the
> non-bypassable control must be a trusted server-side check required by a
> no-bypass GitHub ruleset. Until Graphify covers this repository's high-risk
> configuration surfaces, making its current output mandatory would automate
> false assurance.

## Two further defects in `graphify prs`, confirmed from source

- **Open PRs only.** `cmd_prs` resolves a number via
  `next((p for p in prs if p.number == pr_number), None)` over `fetch_prs()`
  (`gh pr list`, open only) and exits 1 with "not found in open PRs". It cannot
  do a post-hoc audit of a merged PR.
- **`READY` ignores mergeability.** `_classify` (`prs.py:104-119`) returns
  `READY` on CI success + not-draft + not-stale + no changes-requested; it never
  reads `mergeable`. Observed `#878 ✓ READY` while `gh pr view --json mergeable`
  said `CONFLICTING`/`DIRTY`.

## UNVERIFIED

- **codex could not reach the network from its read-only sandbox**, so it could
  not re-query branch protection or ruleset 19868073. Its §B conclusion is
  **conditional on the state this agent measured today** — I did read both
  directly via `gh api`, so the inputs are first-hand, but they are a
  point-in-time snapshot.
- codex could not run `mise run graphify-health` (read-only sandbox blocked
  mise's temp state). This agent ran it separately: `fresh (runtime=0.9.53)`.
  codex reproduced E4 from the raw graph snapshot without independently
  certifying its freshness.
- **Cold-build duration and determinism are unverified.** codex found canonical
  ordering and a fixed seed 42 (`graphify/cluster.py:109-166`) but ran no
  control-arm builds. Whether `community` assignment — which
  `compute_pr_impact` reads — is stable across two clean builds is **open**, and
  it is load-bearing: a non-deterministic community id would make a
  recompute-and-compare gate flap.
- Whether GitHub's ruleset UI can attach a required-status rule pinned to a
  specific App in this repo's plan tier: not probed.
- `.claude/rules/graphify-first.md` was honoured (`graphify-health` → `fresh`);
  the `graphify-query` orientation call returned `TRUNCATED` and errored, so
  source reading was the fallback, per that rule.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under advice: rules, hk config, CI workflow, branch protection, ruleset.
- [graphify (vendored `graphifyy` 0.9.53)](https://github.com/) — read
  `prs.py`, `detect.py`, `cluster.py`, `cli.py`, `__main__.py` from
  `python/.venv/`; upstream repo URL not resolved from the installed package.
