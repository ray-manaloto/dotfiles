# gfy-T3 codex review lenses — commits bcbea39f and 67e0be1d (verbatim final messages)

Commands: `mise exec -- codex exec -s read-only --ignore-rules review --commit <SHA> -c 'sandbox_mode="read-only"' -m gpt-6-astra -c 'review_model="gpt-6-astra"' -c 'model_reasoning_effort="xhigh"'`
for `bcbea39f` then `67e0be1d`; both banners `reasoning effort: xhigh`, both rc=0.
Both diffs Claude-authored, so codex is the cross-family lens.

## bcbea39f

```text
The new prerequisite uses a different release source from the updater, potentially blocking valid operations during publication skew. Runtime validation was blocked by the read-only sandbox's cache and temporary-file restrictions.

Review comment:

- [P2] Gate against the updater's actual package target — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/gfy-t3/python/src/dotfiles_setup/graphify_fleet.py:672-675
  When GitHub publishes a release before the package index exposes it, this gate rejects a host already at the updater's installable target. `gather()` determines currency using `gh release view`, but `graphify_currency.graphify_update_main()` selects its target using `mise latest pipx:graphifyy`. Consequently, a previously valid dotfiles refresh is now blocked, and the suggested host upgrade cannot succeed while that package is unavailable. Resolve the same target as `graphify-upgrade` and compare the host binary against it before refusing.
```

## 67e0be1d

```text
The retirement exception introduces a false-current result for invalid KB source manifests. Runtime validation was blocked by sandbox restrictions on uv cache and temporary-file writes.

Review comment:

- [P2] Preserve manifest validation for PyPI-pinned KBs — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/gfy-t3/python/src/dotfiles_setup/graphify_fleet.py:356-360
  For a PyPI-pinned KB, the two installation revisions legitimately disappear, but `sources/graphify.manifest` still requires a `ref` and `commit`: the KB's `kb_setup.manifest.load()` rejects either field being absent. This exception now reports a URL-only manifest as `current`, exactly as the new test fixture supplies, even though the KB cannot load that manifest to build its graph. Separate the optional fork-revision comparison from manifest validation; retiring the fork must retain the upstream source tag and SHA.
```

## Disposition (added after receipt)

- bcbea39f P2: CONFIRMED for bcbea39f, ALREADY FIXED by its child 67e0be1d —
  `gather()` now takes upstream from `graphify_currency._latest_probe`
  (`mise latest pipx:graphifyy`), the same target `graphify-upgrade` uses, so the
  host-leg gate compares against the updater's own target.
- 67e0be1d P2: CONFIRMED (KB `origin/main:python/src/kb_setup/manifest.py:169`
  requires `{"url", "ref", "commit"}`) and FIXED in the next commit: the manifest
  must always carry url/ref/commit; only the two install revisions may be
  absent together. The test fixture now carries ref + commit and a URL-only
  manifest asserts drift; reverting the check fails that test.

## 71800e4e (verbatim)

```text
The PyPI exception now permits mismatched source and installation pins to report as current. Targeted pytest execution was blocked by sandbox restrictions on uv's cache.

Review comment:

- [P2] Check the PyPI manifest against the installed version — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/gfy-t3/python/src/dotfiles_setup/graphify_fleet.py:363-365
  When a retired-fork KB pins PyPI `0.9.76` but retains a complete manifest for `v0.9.57`, both installation revisions are `None`, so this guard skips the comparison and the required-field check passes. `gather()` consequently reports the KB as `current`, and `plan()` emits no reconciliation step, although the KB source corpus describes an older version than the installed package. Validate the PyPI manifest's release ref and corresponding commit against the installed version rather than checking only that its fields exist.
```

Disposition: CONFIRMED and FIXED for the ref (a PyPI-pinned KB's manifest
`ref` must equal `v<installed version>`; reverting the check fails its test).
NOT FIXED: resolving the manifest `commit` to that tag — it needs the upstream
clone at an arbitrary tag; recorded as residue. This was the second review
round on the retired-fork branch, so per the codex-sdlc-team review-tier rule
(stop after two rounds on one diff) the loop stops here and the residue goes to
the coordinator.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed commits
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `kb_setup/manifest.py` required-field check, to confirm the 67e0be1d finding
