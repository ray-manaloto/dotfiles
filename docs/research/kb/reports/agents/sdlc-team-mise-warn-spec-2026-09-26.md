# Spec — research + fix design for the mise tracked-config WARN pollution (REVIEW / RESEARCH ONLY)

## 1. Objective

Produce a verified fix DESIGN (not an implementation) for issues ray-manaloto/dotfiles#1169 and #1248: the pytest
suites of dotfiles AND knowledge-base register temp `mise.toml` files in the HOST mise state
(`~/.local/state/mise/tracked-configs`, 1,465 links on 2026-09-26, 181 after a `mise prune --configs` on 2026-09-16),
and every host `mise` command then re-parses them, printing e.g.
`mise WARN unknown field in /private/var/folders/.../pytest-839/.../mise.toml: settings.not_a_real_setting`.
The failure prevented: real warnings masked by noise, startup cost, a claude-doctor brick (2026-09-18) from the same
stderr WARN class.

Answer, with evidence:
- Q1. Which mise release since 2026.9.0 (host is 2026.9.14) adds or changes anything relevant: config tracking,
  `mise prune --configs`, a setting or env var to disable/redirect tracking, stale/dangling link cleanup, warning
  de-duplication or suppression for tracked (non-active) configs. Read the real CHANGELOG / GitHub releases of
  jdx/mise and the source (`src/config/tracking.rs` or wherever tracking lives at the current tag) — source beats docs.
- Q2. jdx/mise GitHub issues, PRs AND discussions on tracked-configs pollution, temp-dir tracking, `MISE_STATE_DIR`
  test isolation, warnings from non-active tracked configs. Merged=false is not "didn't ship" — check.
- Q3. The complete set of test sites in BOTH repos that run a real `mise` binary against a temp dir (grep for
  subprocess calls to mise and for writes of `mise.toml` / `.mise.toml` under tmp_path), and the single cleanest
  isolation seam per repo (conftest autouse fixture vs a shared helper). Which env var(s) actually stop tracking:
  `MISE_STATE_DIR`? something else? PROVE it with a live arm: run `mise` against a throwaway temp dir with and without
  the candidate env var, counting links in a throwaway state dir you point at — never mutate the host state dir.
- Q4. A safe, bounded cleanup for the host (native verb first — `mise prune --configs`? does it remove links whose
  target still EXISTS in a pytest tmp dir?). Report what it would remove via its dry-run flag if it has one; do NOT
  run a mutating cleanup on the host.
- Q5. Recommended fix: files, the shape of the fixture, and the regression test (host tracked-configs count unchanged
  by a mise-invoking test; the temp state dir gained a link), with its fail arm.

## 2. Files

READ ONLY. Repos: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` and
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base`. Write NOTHING in either repo. Scratch experiments go
under `$TMPDIR` in a directory you create and delete. Your final message is the deliverable (captured by the
supervisor).

## 3. Interfaces

Final message sections, in order: `## Q1` … `## Q5`, `## Evidence table` (claim | source URL or file:line | probe +
control arm), `## GitHub repos touched` (owner/repo — one-line reason), `## Open questions`.

## 4. Constraints and invariants

- NEVER run `mise prune`, `mise trust`, `mise use -g`, `rm`, or anything that mutates `~/.local/state/mise` or
  `~/.config/mise`. Point `MISE_STATE_DIR` (and any other candidate) at a temp dir for every experiment.
- Never print environment values or credentials. GitHub access: `gh api` (search: `gh api '/search/issues?q=repo:jdx/mise+<terms>'`
  — `gh search issues --repo` returns 0 silently on this host); discussions via `gh api graphql`.
- Docs: `curl https://mise.jdx.dev/llms.txt` then per-page fetches; `ctx7` CLI; GitHub raw source at the release tag.
- Every negative finding ("no setting exists") needs a control arm: the same probe finding something known to exist.
- `timeout` is a broken shim on this host; bound with `perl -e 'alarm N; exec @ARGV' <cmd>`.
- Do not pipe gate output into head/tail.

## 5. Verification

The Q3 live arm (with/without the env var, link counts in a temp state dir) printed verbatim, and at least one
jdx/mise source file:line at the current tag for every mechanism claim.

## 6. Commit

caller (nothing to commit; research only).

## 7. PREMISES

- L: host mise = 2026.9.14 — `mise --version` this session.
- L: WARN source test writes `[settings]\nnot_a_real_setting = true` — knowledge-base `tests/test_evals.py:581`.
- L: neither repo's tests set `MISE_STATE_DIR` — grep of `tests/` in both repos this session (only hit:
  dotfiles `python/src/dotfiles_setup/fnhook_gates.py`, not a test).
- L: tracked-configs link count 1,465 — `ls ~/.local/state/mise/tracked-configs | wc -l` this session.
- P: #1169 proposes `MISE_STATE_DIR=<tmp>` isolation; #1248 says `mise prune` prunes tool versions, not configs —
  whereas #1169 reports `mise prune --configs` took 5,295 → 181. These two issue claims CONFLICT; resolve it.
- A: `mise prune --configs` exists at 2026.9.14 — unverified; check `mise prune --help`.
