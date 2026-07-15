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

## Honest note on adoption

These labels exist but are **not yet in use** — no issue carries one today. `/triage` is
`disable-model-invocation: true`, so only a human typing `/mattpocock-skills:triage` drives it. This
file records the vocabulary so the skill works when reached for; it does not assert a practice we
have.

The one wiring in place: `refresh.yml`'s tool-currency issue is labelled `needs-triage` on creation,
so bot-filed issues enter the flow rather than sitting unlabelled (25 of the last 60 issues have no
label at all).

## See also

- `docs/issue-tracker.md` — the tracker config these skills read.
