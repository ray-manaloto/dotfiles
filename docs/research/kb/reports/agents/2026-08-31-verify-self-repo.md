# Verify: is `uses: $/...` a real GitHub Actions syntax?

## Source 1 — GitHub official workflow-syntax docs (PRIMARY, fetched 2026-08-31)
URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
Fetched: 2,020,161 bytes HTML -> 149,539 chars text.

VERDICT FROM THIS SOURCE: **SUPPORTED and RECOMMENDED.** 18 occurrences of `$/`.

Key quotes (tag-stripped, whitespace-normalised):

> Example: Using an action in the same repository as the workflow at the running commit (recommended)
> `$/path/to/action`
> The `$/` prefix is the self repository reference. It references an action stored in the same
> repository as the workflow or action ... so it is the recommended way to reference an action
> within its own repository.

> The `$/` syntax is not available in GitHub Enterprise Server.
> A `$/` reference must not include an `@{ref}` suffix. The ref is always the commit the running
> workflow or action is using, so a reference such as `$/actions/my-action@v1` is invalid.

> `$/` always resolves against the repository of the file it appears in, not the repository that
> called it. ... This makes `$/` reliable for action composition, where a relative `./` path would
> instead resolve against whatever is checked out in the caller's workspace.

Comparison table row:
> Syntax `$/path/to/action` | Resolves to: The same repository as the running workflow or action,
> at the running commit | Recommended for: Actions in the same repository

Worked example in the docs:
>       steps:
>         # References an action in the same repository at the running commit
>         - uses: $/.github/actions/hello-world-action

On `./`:
> ... a relative path resolves against the runner's workspace rather than the repository of the
> running workflow. For most cases, use the `$/` syntax shown above instead.

Reusable workflows section:
> `$/.github/workflows/{filename}` for a reusable workflow in the same repository. This is the
> recommended syntax...
> A `$/` reference must not include an `@{ref}` suffix, and `$/` is not available in GitHub
> Enterprise Server.

## CONTROL ARM (source 1)
Same extraction + same grep shape, terms known to be documented on that page:
- `docker://` -> 6 hits  (known-documented syntax: PRESENT)
- `./.github` -> 8 hits  (known-documented local ref: PRESENT)
- `self-repository` -> 0 hits (zizmor's audit NAME, not expected in GitHub docs)
So the probe discriminates: it returns hits for known-present terms and zero for a known-absent one.

## Pending
- [ ] GitHub Changelog entry / date
- [ ] zizmor docs self-repository audit
- [ ] actionlint issue 711

## Source 2 — zizmor docs (https://docs.zizmor.sh/audits/) fetched 2026-08-31
`self-repository` audit, "Introduced in v1.30.0", auto-fixes available:
> As of July 2026, GitHub supports a new "self-repository" syntax (`uses: $/...`) when referring
> to actions or reusable workflows within `uses:` clauses.
Benefits it claims: not subject to runtime filesystem state (can't load an action cloned at
runtime in a previous step); counts as a form of pinning so a "fully pinned" org policy can be
enforced. Links to the GitHub changelog entry below.

## Source 3 — GitHub Changelog (PRIMARY) — HTTP 200
URL: https://github.blog/changelog/2026-07-30-reference-same-repository-actions-with-self-repository-syntax/
Dated **July 30, 2026**, tagged "Release".
> You can now reference an action or reusable workflow that lives in the same repository using
> the new self-repository syntax. A `uses:` value that starts with `$/` resolves to your
> workflow's own repository at the exact commit that is running, with no checkout required. It
> works everywhere the workspace-relative `./` syntax works, including workflow steps, composite
> action steps, nested composition, and reusable workflow calls.
> ... Self-repository references are now the recommended way to compose actions and reusable
> workflows within a repository. They are available on github.com. **This feature requires the
> GitHub Actions runner to be on version 2.336.0 or newer.**

CAVEATS (from sources 1 + 3):
- github.com only; **NOT available on GitHub Enterprise Server**.
- Requires Actions runner **>= 2.336.0** (relevant to self-hosted runners; GitHub-hosted runners
  are current).
- `@{ref}` suffix is INVALID on a `$/` reference (`$/actions/my-action@v1` is invalid).
- `refs/heads` / `refs/tags` prefixes not allowed.
- Resolves against the repo of the FILE it appears in, not the caller's repo.

## Source 4 — actionlint issue rhysd/actionlint#711 (via `gh api`, PRIMARY)
Title: "Support the new `$/` self-repository `uses:` syntax" — opened 2026-07-30 by tristanbes,
**state: open** (as of 2026-08-31). Latest actionlint release is **v1.7.12, published 2026-03-30**
— i.e. predates the feature; no release since.
Body confirms actionlint 1.7.12 rejects it:
> example.yml:8:15: specifying action "$/.github/actions/my-action" in invalid format because ref
> is missing. available formats are "{owner}/{repo}@{ref}" or "{owner}/{repo}/{path}@{ref}" [action]
Workaround given in the issue:
> actionlint -ignore 'specifying action "\$/.+" in invalid format because ref is missing'
A commenter (muzimuzhi) adds the `paths.<glob>.ignore` config-file equivalent.

## FINAL VERDICT: SUPPORTED — high confidence
`$/` is real, documented in GitHub's official workflow-syntax reference, shipped via a dated
changelog entry (2026-07-30), and is GitHub's *recommended* form for same-repo references.
The runtime risk is NOT the runner — it is `actionlint`, which fails the file until #711 lands.
