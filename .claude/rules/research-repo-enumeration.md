# Research Repo Enumeration: List Every Touched Repo

Every research artifact produced by an agent — deep reviews, spec
deltas, doc lookups, dependency audits — MUST end with a `## GitHub
repos touched` section listing every owner/repo URL whose source or
docs were consulted while producing the artifact.

## Why

Research artifacts accumulate over time. Without an enumeration section,
it becomes impossible to answer "which repos have we already researched?"
or "which repos does this finding depend on?" without re-reading every
artifact. The enumeration section is the cheap-to-grep index that makes
artifacts bisectable after the fact.

It also feeds `docs/research/mintlify-catalog.md`: any repo enumerated
in a research artifact should either already be in the catalog or be
appended to its request queue during the same commit.

## Format

At the bottom of every research artifact:

```markdown
## GitHub repos touched

- [owner/repo](https://github.com/owner/repo) — one-line reason
- [owner/repo](https://github.com/owner/repo) — one-line reason
```

Rules:

- Every repo whose source files, README, issues, or docs were read.
- Every repo whose mintlify site was queried (via `llms.txt`, `.md`, or
  `mcp2cli`).
- One-line reason per entry — just enough to grep for later.
- Empty section is allowed (`## GitHub repos touched\n\n_None._`) if the
  artifact truly touches zero repos (rare).

## Applies to

- `.omc/research/**/*.md` — agent working research (gitignored by
  default via per-clone exclude, but still subject to this rule inside
  the scratchpad for consistency).
- `docs/research/**/*.md` — tracked research artifacts that ship in the
  repo.
- Any other markdown artifact produced by a research workflow (deep
  review, spec delta, dependency audit, etc.).

## Not applies to

- Plans (`.omc/plans/**`, `docs/research/plans/**`) — plans describe
  intended work, not research findings.
- Session handoffs (`.omc/plans/session-*.md`) — the repos touched are
  implied by the commits in the session.
- Rule files, skill files, CLAUDE.md.

## Enforcement

For tracked research artifacts, this rule is documented but not yet
machine-enforced: `.omc/research/**` is gitignored at the per-clone
level, so an hk grep-check on staged `.omc/research/*.md` files is a
no-op in this repo. A future commit can add an hk step targeting
`docs/research/**/*.md` when the first tracked research artifact lands;
until then, this rule relies on reviewer enforcement.

## See also

- `.claude/rules/research-doc-sources.md` — the sibling preference
  chain for fetching doc content.
- `docs/research/mintlify-catalog.md` — the repo catalog that
  enumeration feeds into.
- `.claude/rules/notepad-enforcement.md` — the "write findings as you
  go" rule; enumeration is the final step before committing a finding.
