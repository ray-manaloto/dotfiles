# Saved-search diff identity review (#1502) — 2026-10-03

Read-only review of how `research-saved-search rerun` decides that a hit is the
same hit as last run. Worktree `dotfiles.worktrees/saved-searches-1502`, branch
`feat/1502-saved-searches` (uncommitted). Only this file was written.

## Code read (file:line)

- `python/src/dotfiles_setup/saved_searches.py:69` — `_BLOB_REF = ^(https://github\.com/[^/]+/[^/]+/blob/)[^/]+/`
- `:515-523` `_canonical` (rewrites the first segment after `/blob/` to `HEAD`)
- `:526-531` `_urls` (canonicalises `html_url` or `url` of every item, all kinds)
- `:808-861` `_report` (canonicalises PREVIOUS urls too, then set-diffs NEW/GONE)
- `:768-801` `_previous` (newest snapshot, else the TOML's newest `[[result]]`); decode failure of ANY snapshot raises `_invalid` (`:776-778`) — a hard fail, not a skip
- `:264-297` `_probe_record` stores raw sha-form `item["html_url"]` into baselines; `:226-261` `_fanout_record` stores fan-out `item["url"]`
- `:460-512` `_direct`: code = `search/code` best-match, issues = `search/issues` best-match (no `sort`), discussions = GraphQL `url`
- `:534-567` `_confirmed` fetches `item["url"]` (the contents API URL), not `html_url`
- `generated/saved_search_snapshot.py` — `WatchRun.urls: list[str]`; base `Struct(forbid_unknown_fields=True)`; `schemas/saved-search-snapshot.schema.json` lists every WatchRun field as `required`
- `generated/saved_search_file.py:63-71` — `Result.urls: list[str] | UnsetType = UNSET` (the optional-field pattern codegen already emits)
- `research_fanout.py:594` issues fan-out = `/search/issues?q=repo:..&per_page=N` (best match, no sort); `:646-690` releases = `repos/{repo}/releases?per_page=100`, item url = `html_url`; `:1693` code-search probe; `:1722-1730` repo-check already reads `full_name` to detect renames (precedent)
- `tests/test_saved_searches.py:740-745` — the existing sha-form → HEAD regression test

## Primary-source evidence

### GitHub REST docs (fetched 2026-10-03 via `docs.github.com/api/article/body?pathname=/en/rest/search/search`, saved `.agent/gh-rest-search.md`)

- Search code item schema: `name`, `path`, `sha`, `url`, `git_url`, `html_url` all **required**; `repository` (Minimal Repository) with `id` (int64), `node_id`, `full_name`, `fork` required.
- "Only the default branch is considered." / "Only files smaller than 384 KB are searchable."
- `sort` for code: "This field is closing down … Can only be `indexed` … Default: best match". Ranking section: "Unless another sort option is provided … results are sorted by best match".
- Search issues: item has `html_url`, `url`, `id`, `node_id`, `number` (required); `sort` may be `created` or `updated` ("You can also sort results by how recently the items were created or updated").
- Legacy code-search syntax (`/en/search-github/searching-on-github/searching-code`, saved `.agent/gh-searching-code-legacy.md:25-26`): forks are indexed ONLY when the fork has more stars than the parent and ≥1 pushed commit, and appear only with `fork:true`/`fork:only`; only the default branch is indexed. Qualifier list (`:36-101`) has **no date qualifier** (no `pushed:`/`created:`).
- Renaming a repository (`/en/repositories/.../renaming-a-repository`, `.agent/gh-rename.md:5`): "all existing information … is automatically redirected to the new name"; `:28` redirects break if the old name is reused.

### Real API output (one `gh api -X GET search/code -f q='include-what-you-use filename:Dockerfile' -f per_page=2`, rc=0)

```
total_count 221, incomplete_results false
item 1: path .gitlab/ci/docker/debian13-x86_64/Dockerfile
  sha      defa93fd3a8ef58f5a87b3dc2f2b92db78f235f8
  url      https://api.github.com/repositories/537699/contents/.gitlab/ci/docker/debian13-x86_64/Dockerfile?ref=c579da7b31afc4fbac30676e03406333affd463a
  git_url  https://api.github.com/repositories/537699/git/blobs/defa93fd3a8ef58f5a87b3dc2f2b92db78f235f8
  html_url https://github.com/Kitware/CMake/blob/c579da7b31afc4fbac30676e03406333affd463a/.gitlab/ci/docker/debian13-x86_64/Dockerfile
  repository.full_name Kitware/CMake, repository.id 537699, fork false
item 2: magma/magma .devcontainer/Dockerfile, sha 3e8a5b3f…, html_url …/blob/76d9dc0e…/.devcontainer/Dockerfile, repository.id 170803235
```

Control arms run on the same item:
- `gh api repos/Kitware/CMake/contents/<path> --jq .sha` → `defa93fd…` (= item `sha`): `sha` is the **blob** (content) sha, also proven by `git_url …/git/blobs/<sha>`.
- `gh api repos/Kitware/CMake/commits/HEAD --jq .sha` → `c579da7b…` (= the `html_url` ref): the html_url ref is the **default-branch head commit at index time**, which moves on ANY push to the repo even when this file is unchanged.
- `gh api repositories/537699 --jq .full_name` → `Kitware/CMake`: the numeric id in `url` resolves, so `repository.id` is a usable rename-stable key.
- Issue/PR probe (`search/issues?q=repo:cli/cli+is:pr+is:merged&per_page=1`): PR `html_url` = `https://github.com/cli/cli/pull/14577`, its API `url` = `…/repos/cli/cli/issues/14577`; issue `html_url` = `…/cli/cli/issues/14584`. No ref in either; form differs by type but is fixed per item.
- Release probe (`repos/cli/cli/releases?per_page=1`): `html_url` = `…/releases/tag/v2.102.0`, `id` 399674740, `tag_name` v2.102.0 — the URL is keyed by TAG NAME, the `id` by release.

### Measured on the two real local snapshots (`.agent/kb/raw/saved-searches/iwyu/`, 6 min apart)

- Run 1 (`20261003T165634Z`) stores sha-form code URLs; run 2 (`20261003T170250Z`) stores HEAD-form.
- Canonicalising run 1 with the same regex and diffing against run 2 (all code watches, keyed id|query|url): **65 vs 65, only_old=0, only_new=0**.
- Control arm, raw (un-canonicalised) run 1 vs run 2: **only_old=65** — every hit churned. The probe discriminates; `_canonical` removes exactly the commit-ref churn.
- Tracked baselines `docs/research/saved-searches/*.toml` contain **0** `/blob/` URLs (grep -c), so no tracked file carries sha-form code URLs today; only local snapshots do.

## Options

| Option | Pros | Cons | Citations |
|---|---|---|---|
| **A. Canonical HEAD URL** (current: regex `/blob/<ref>/`→`/blob/HEAD/` on new AND previous URLs) | Measured fix: 65/65 churn → 0. No schema change; old sha-form snapshots and any URL-only baseline canonicalise on read, so it is the ONLY key derivable from every previous source. HEAD URL is a valid, always-resolving display link. Both sides go through the same regex, so percent-encoding is consistent. Regex is anchored, so a path containing `/blob/` is untouched. | Implicit: identity is a string convention, not a field. Loses the exact-version permalink (the snapshot no longer says which content matched). Cannot see a content change of an unchanged path. Rename/transfer → NEW+GONE pair (same for B by full_name). Only `https://github.com` matches (GHES would silently fall back to raw churn). Applied to all kinds (harmless — issue/PR/release/discussion URLs have no `/blob/`). | `saved_searches.py:69,515-531,826-827`; real `html_url` ref = HEAD commit (`commits/HEAD` probe); snapshot diff 0 vs control 65 |
| **B. Explicit key `(repository.full_name, path)` stored separately from display URL** | Explicit and self-documenting; the display URL could stay a permalink. Uses required fields (`full_name`, `path`). | Needs a schema change (new optional field); previous snapshots and baselines hold URLs only, so you STILL need A's URL parse to key them — two code paths that must agree (path from API is unencoded, path in html_url is percent-encoded: a constructed key can mismatch a parsed one). Same rename behaviour as A. No new information vs A. | REST schema (`full_name`, `path` required); `saved_search_file.py:71` URL-only baselines; `_probe_record` `:292` |
| **B'. Key `(repository.id, path)`** | Rename- AND transfer-stable (id survives; `url` already embeds `/repositories/<id>/`). | Not derivable from any html_url, so every URL-only baseline and every existing snapshot reports a one-time full NEW/GONE; extra field required. Renames are rare and redirected anyway. | real `url` …`/repositories/537699/…`; `repositories/537699` → Kitware/CMake; rename doc `:5` |
| **C. Key on item `sha`** (blob sha) | Stable while content is unchanged; content-addressed. | WRONG identity: changes on every edit of the file (a real edit reads as GONE+NEW), and identical content in many repos/forks/vendored copies collapses to one key (the same blob in N repos = 1 hit). Not present in any URL-only baseline. | `git_url …/git/blobs/<sha>`; contents probe `.sha` = item sha |
| **D. Hybrid: identity = repo+path (A's key), plus CHANGED when the blob `sha` differs from last run** | Keeps A's churn-free identity and back-compat; adds a genuine signal — the same file was edited (e.g. a Dockerfile bumping to a newer clang) — which is relevant to "newer examples". Blob sha is required in every code item. Optional field → old snapshots still decode. | Schema change (optional field). CHANGED is only computable when BOTH runs stored a sha (no CHANGED on the first run after the change, or vs a URL-only baseline). Some CHANGED noise from unrelated edits to the same file. Code kind only. | REST schema `sha` required; codegen optional pattern `saved_search_file.py:68-71`; `_previous` hard-fails on undecodable snapshots `:776-778` |
| **E1. Native recency: `sort=created&order=desc` for issues/PRs** (and `created:>DATE` qualifiers) | Native GitHub feature; makes the top-N window actually "newest first", so NEW really means new. | Issues only; changes the result set of existing watches once (one-time NEW/GONE). Code search has NO date sort (`sort=indexed` is "closing down") and NO date qualifier. | REST search/issues `sort` param; search/code `sort` param; legacy qualifiers list |
| **E2. Mark the diff as a WINDOW when `count > len(urls)`** | Code search is best-match over 221 hits but stores 10: NEW/GONE among a truncated best-match page is ranking churn, not novelty. Flagging it (or raising `limit` up to 100 when `total_count ≤ 100`) is the honest fix for "find newer examples". | Does not change identity; raising `per_page` spends the same 1 request (max 100/page) but larger snapshots. | "up to 100 results per page"; Ranking = best match; real `total_count 221` with 10 stored |
| **E3. A native GitHub "saved search / alert" for code** | — | None found: the REST search docs expose no saved-search, subscription or webhook for code search; repo "watch → releases" notifications are per repo, not per query. Not a replacement. | REST search page (no such endpoint) — negative result, armed only by reading the whole endpoint list on that page |

## Edge cases

1. **Repo rename / transfer.** A later search returns the NEW `full_name` in `html_url`; old URLs redirect (rename doc `:5`). A, B and D report one GONE (old name) + one NEW (new name) for each hit; B' (repository.id) does not. Acceptable and arguably informative; do not pay B''s baseline-incompatibility for it.
2. **Forks.** Indexed only when the fork has more stars than its parent AND ≥1 pushed commit, and returned only with `fork:true`/`fork:only` (legacy doc `:25`). When included, a fork and its parent are different `full_name`s → distinct keys under A/B/D (correct: two places the example lives). Under C they collapse when the file is byte-identical (wrong).
3. **Same path in a different repo.** Distinct under A/B/D (key includes owner/repo); collapses under C if content is identical.
4. **Path containing `/blob/`.** `_BLOB_REF` is `^`-anchored and `[^/]+` for owner, repo and ref, so only the segment right after the first `/blob/` is rewritten; a later `/blob/` in the path is untouched. A repo literally named `blob` (`github.com/o/blob/blob/<sha>/p`) also canonicalises correctly (owner=o, repo=blob). Worth one parametrised test case; current test (`tests/test_saved_searches.py:740-745`) covers only `same.rs`.
5. **Issues / PRs.** `html_url` carries no ref and is stable per item; PRs are `/pull/N`, issues `/issues/N` (probe above). An item never switches between the two forms. Transfer of an issue to another repo yields a new URL (GONE+NEW) — not verified live here (no transferred item at hand; UNVERIFIED). Discussions (GraphQL `url`) have the same shape.
6. **Releases.** `html_url` is `/releases/tag/<tag_name>` — stable unless the release's tag is renamed (then GONE+NEW; `id` would survive). Deleting and re-creating a release on the SAME tag keeps the same URL, so a re-tag/re-publish is INVISIBLE to a URL diff (only `id`/`published_at` change). Draft releases are not in the list for read-only callers. For "newer examples" a new tag is a new URL, which is what matters.
7. **Baseline from older reports (sha-form or HEAD-form).** A canonicalises both forms to the same string (`_report:827`), so a `_probe_record` baseline with sha-form `html_url` (`:292`) and a HEAD-form snapshot compare correctly. A branch-name ref (`/blob/main/…`) also canonicalises. Today the tracked baselines hold 0 `/blob/` URLs; the fix still matters because `record` writes raw sha-form `html_url`s into future baselines (`_probe_record:292`). Optional: canonicalise there too, so the tracked TOML never stores a moving ref.
8. **Backward compatibility with written snapshots.** Snapshots are gitignored local files (`.agent/kb/raw/saved-searches/`); two exist. `_previous` RAISES on any snapshot that fails to decode (`:776-778`) and the model forbids unknown fields, so: (a) any new snapshot field must be NON-required in the schema (codegen then emits `| UnsetType = UNSET`, as for `Result.urls`) or every old snapshot hard-fails the next rerun; (b) an older binary reading a NEW snapshot will hard-fail on the unknown field (forward-incompatible — acceptable on an unshipped branch, but say so).
9. **Truncated best-match window (the bigger "find newer examples" problem).** Measured: `iwyu-dockerfile-musthit` count 221, 10 URLs stored. Best-match ordering can move hits in/out of the top 10 with no change in the world. No identity choice fixes this; E2 does.

## RECOMMENDATION

**Keep A as the identity, and add D's CHANGED signal plus E2's window flag. Do not adopt B/B'/C.**

Rationale: the canonical HEAD URL already IS the `(full_name, path)` key of option B, and it is the only key derivable from URL-only baselines and the two existing snapshots, so B adds a second code path with no new information. C is the wrong identity (content-addressed). D is the one extension that adds real "newer example" signal.

Exact code change:

1. `_canonical` / `_urls` (`saved_searches.py:515-531`): unchanged. Add test cases for a path containing `/blob/`, a repo named `blob`, a `/blob/main/` baseline URL, and non-blob URLs (issue, `/pull/`, `/releases/tag/`) passing through.
2. `_probe_record` (`:292`): store `_canonical(item["html_url"])` so tracked baselines never persist a moving commit ref.
3. Schema `schemas/saved-search-snapshot.schema.json` `WatchRun`: add NON-required `"shas": {"type": "object", "additionalProperties": {"type": "string"}}` (canonical URL → blob `sha`); regenerate `generated/saved_search_snapshot.py` (codegen emits `shas: dict[str, str] | UnsetType = UNSET`, old snapshots still decode).
4. `_run_code` (`:682-694`, the `WatchRun(...)` with `_urls(answer)` at `:690`): pass `{_canonical(item["html_url"]): item["sha"] for item in answer.items if both are str}` as `shas`; `_run_other` leaves it UNSET.
5. `_Previous` (`:757-762`) gains `shas: dict[str, str]`; `_previous` fills it from `_given(run.shas, {})` (baselines: `{}`).
6. `_report` (`:808-861`): add a `CHANGED` column = `sorted(u for u in set(run.urls) & old_urls if u in old.shas and u in new.shas and old.shas[u] != new.shas[u])`; and when `run.count > len(run.urls)` append ` (top {len(run.urls)} of {run.count}; NEW/GONE is ranking churn)` to the status cell (E2).
7. Separately (E1, issues only): add `&sort=created&order=desc` to the draft issues query in `_direct` (`:475`) so the stored window is newest-first; expect a one-time NEW/GONE on existing issue watches. Code search cannot do this (no date sort or qualifier).

Spec §3.3/§4.4 (`docs/specs/research-saved-searches-1502.md:143-145, 202-207`) should be updated in the same change to name the canonical-URL identity, the optional `shas` map and the CHANGED column.

## GitHub repos touched

- [Kitware/CMake](https://github.com/Kitware/CMake) — real code-search item; contents/commits probes proving `sha`=blob, html_url ref=HEAD commit
- [magma/magma](https://github.com/magma/magma) — second real code-search item
- [cli/cli](https://github.com/cli/cli) — issue/PR html_url forms and release html_url/id/tag_name probes
- [github/docs](https://github.com/github/docs) — REST search docs, legacy code-search syntax, repository-rename doc (fetched via docs.github.com)
