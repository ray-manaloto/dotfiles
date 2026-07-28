# Research Repo Enumeration: List Every Touched Repo

Every research artifact produced by an agent — deep reviews, spec
deltas, doc lookups, dependency audits — MUST end with a `## GitHub
repos touched` section listing every owner/repo URL whose source or
docs were consulted while producing the artifact.

## Why

Without an enumeration section you cannot answer "which repos have we
already researched?" without re-reading every artifact. It is the
cheap-to-grep index that makes artifacts bisectable after the fact, and
it feeds `docs/research/mintlify-catalog.md` — a repo enumerated in an
artifact should already be in the catalog, or be appended to its request
queue in the same commit.

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

- `docs/research/runs/**/*.md` — agent working research (gitignored by
  default via per-clone exclude, but still subject to this rule inside
  the scratchpad for consistency).
- `docs/research/**/*.md` — tracked research artifacts that ship in the
  repo.
- Any other markdown artifact produced by a research workflow (deep
  review, spec delta, dependency audit, etc.).

## Not applies to

- Plans (`.agent/plans/**`, `docs/research/plans/**`) — plans describe
  intended work, not research findings.
- Session handoffs (`.agent/plans/session-*.md`) — the repos touched are
  implied by the commits in the session.
- Rule files, skill files, CLAUDE.md.

## Enforcement

**Reviewer-enforced, not machine-enforced.** An hk grep-check on staged
`docs/research/runs/*.md` would be a no-op — that tree is gitignored, so
nothing is ever staged from it. A step targeting `docs/research/**/*.md`
becomes worth adding once tracked research artifacts are routine.

## See also

- `.claude/rules/research-doc-sources.md` — the sibling preference
  chain for fetching doc content.
- `docs/research/mintlify-catalog.md` — the repo catalog that
  enumeration feeds into.
- `.claude/rules/notepad-enforcement.md` — the "write findings as you
  go" rule; enumeration is the final step before committing a finding.
