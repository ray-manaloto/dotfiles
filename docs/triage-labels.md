# Triage Labels

The mattpocock engineering skills speak in terms of five canonical triage roles. This file maps
those roles to the actual label strings on
[`ray-manaloto/dotfiles`](https://github.com/ray-manaloto/dotfiles). Read by
`/mattpocock-skills:triage`.

**The mapping is the identity.** We adopted the canonical vocabulary verbatim rather than
translating it, so there is no remapping layer to keep in sync.

| Canonical role | Our label | Meaning | Status |
|---|---|---|---|
| `needs-triage` | `needs-triage` | Not yet assessed | created 2026-07-15 |
| `needs-info` | `needs-info` | Blocked pending information | created 2026-07-15 |
| `ready-for-agent` | `ready-for-agent` | Fully specified; an agent can take it unattended | created 2026-07-15 |
| `ready-for-human` | `ready-for-human` | Needs human judgement | created 2026-07-15 |
| `wontfix` | `wontfix` | Will not be actioned | pre-existing (GitHub default) |

When a skill mentions a role ("apply the AFK-ready triage label"), use the label string above.

## These are STATE labels — orthogonal to our type labels

They answer *where is this in the flow*. The repo's existing vocabulary answers *what kind of thing
is this*, and is unaffected:

| Type label | Live usage (last 60 issues) |
|---|---|
| `enhancement` | 23 |
| `bug` | 8 |
| `dependencies` | 5 (bot PRs) |
| `lockfile` | refresh.yml's lock-refresh PRs |
| *(unlabelled)* | 25 |

**Both axes coexist on one issue** — `enhancement` + `ready-for-agent` is the normal shape, not a
conflict. Nothing here changes how `enhancement`/`bug`/`dependencies` are used.

## Adoption — measured 2026-08-08, not asserted

The labels **are** in use, but coverage is thin. Counted over all open issues at
`gh issue list --state open --limit 500` (an explicit limit that exceeds the population — the
default view is a display bound, and reading it at ~40 rows once flipped this very conclusion):

| | before the session | after |
|---|---|---|
| open issues | 135 | **134** |
| carrying a **state** role | **15** | **15** |
| carrying a **category** role (`bug` / `enhancement`) | 40 | 40 |
| **no labels at all** | 39 | **37** |

The delta reconciles exactly: `#421` closed as already-implemented and `#193` labelled
`dependencies`, both of which were previously unlabelled. Nothing else moved.

State-role spread: `needs-triage` 5, `ready-for-agent` 5, `ready-for-human` 4, `needs-info` 1,
`wontfix` 0.

⚠️ **`wayfinder:*` labels are NOT state roles** (12 `task`, 11 `grilling`, 8 `research`,
4 `prototype`, 2 `map`). An issue can carry three of them and still be untriaged — do not read them
as triage coverage.

`/triage` is `disable-model-invocation: true`, so only a human typing `/mattpocock-skills:triage`
drives it; coverage grows only when someone sits down and runs it.

The one automatic wiring: `refresh.yml`'s tool-currency issue is labelled `needs-triage` on
creation, so bot-filed issues enter the flow rather than sitting unlabelled.

### Bot-filed issues get a category label, not triage

A permanent bot artifact is not a request and should not sit in the untriaged bucket. Precedent:
`#184` (tool-currency report, `app/github-actions`) carries `dependencies`; `#193` (Renovate's
Dependency Dashboard, `app/renovate`) was unlabelled until triage on 2026-08-08 gave it the same
label. Label them and leave them open — do **not** close them, Renovate needs its dashboard.

> **Superseded 2026-08-08.** This section previously read *"These labels exist but are **not yet in
> use** — no issue carries one today"* and cited *"25 of the last 60 issues have no label at all"*.
> The first claim was false by the time it was read; the second used a different denominator (last
> 60 issues) than the table above (all open issues), so the two numbers are not comparable.

## See also

- `docs/issue-tracker.md` — the tracker config these skills read.
