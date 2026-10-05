---
name: graphify-fleet
description: Report and advance every graphify pin across dotfiles, the knowledge-base fork pin and the host via `mise run graphify-fleet -- status|plan|apply --leg <dotfiles|kb|host>`. Use when a new graphify release lands, when deciding which repo is behind, or before a fork rebase or KB pin move.
user-invocable: true
---

# Graphify fleet

Graphify is pinned in three independent **legs**. This task reads all three at
once and orders the work; each leg's own tooling still does the writing.

| Leg | Pin it reads | Writer |
|---|---|---|
| `dotfiles` | `python/uv.lock` + the three `.graphify_version` stamps (via `graphify_currency.check`) | `mise run graphify-upgrade` |
| `kb` | the KB clone's `origin/main`: `pyproject.toml` `==` pin + fork `rev`, `uv.lock`, `sources/graphify.manifest`, `currency.toml` fork `base_ref` | fork replay (human) → KB `kb-graphify-pin` (wired in T8) |
| `host` | `~/.config/mise/config.toml` `pipx:graphifyy`, the PATH binary, `uv tool list` | you, by hand |

## Steps

1. **Status.** `mise run graphify-fleet -- status` (add `--json` for the typed
   `FleetPlan`). One network call — `gh release view` for upstream latest; the
   KB and the fork clone are read from local refs and never fetched, so fetch
   them yourself first when freshness matters. Done when you have read the
   `verdict` line and every `finding`.
2. **Plan.** `mise run graphify-fleet -- plan`. Done when every `HUMAN` step has
   an owner: the fork replay is always human-reviewed, and the host leg is a
   user-level change (`feedback_no_user_level_file_updates`).
3. **Apply the dotfiles leg** on a branch: `mise run graphify-fleet -- apply
   --leg dotfiles` (= `graphify-upgrade`), then ship it via `pr-workflow`.
4. **The KB leg.** Hand the fork replay to a fork-scoped lane: the plan prints
   the `fork-maintenance preview --candidate <KB commit>` command and the
   `rebase --onto` fallback. `apply --leg kb` refuses (rc=2) until T8 wires
   `kb-graphify-pin`; run that KB task in the KB checkout after the new fork
   commit is pushed.
5. **The host leg.** `apply --leg host` prints the commands (`uv tool uninstall
   graphifyy`, `mise use -g pipx:graphifyy@<latest>`); run them yourself, then
   `exec $SHELL` and re-run status.
6. Re-run `status`. Done when the verdict is `current (rc=0)`.

## Reading the output

- **rc** follows `DriftVerdict`: 0 every leg current, 1 a leg is `behind` or
  in `drift`, 2 something is `unverifiable`. Severity: unverifiable > behind >
  drift > current; the worst leg is the verdict.
- `UNVERIFIABLE: …` names a probe that could not answer — a missing ref, an
  absent tag, a failed `gh`. Resolve it; it never counts as current.
- **fork-probe** greps upstream's latest tag in the local fork clone for the
  fork-only features (`openai-cli`, `fallback-backend`) against the control arm
  `claude-cli`. A control count of 0 means the probe is blind, and a behind KB
  then turns the verdict `unverifiable`. `native=True` means upstream now ships
  every fork feature: retiring the fork (manifest `clears_when`) is a human
  decision, and the plan says so instead of printing a rebase.
- KB `drift` means its own sites disagree (pyproject vs `uv.lock` vs manifest
  commit vs `base_ref`) — reconcile those before any version move.

Logic: `python/src/dotfiles_setup/graphify_fleet.py` (its docstring records why
Renovate, `kb-currency` and the vendor `graphify update` do not cover this).
Typed output: `schemas/graphify-fleet.schema.json` → `mise run codegen`.
