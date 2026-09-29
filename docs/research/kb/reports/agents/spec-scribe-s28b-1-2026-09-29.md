# spec-scribe — S28b-1 spec draft final report (session dcb0b106, 2026-09-29)

Verbatim final message. Spec: `docs/specs/s28b-1-p2996-single-literal.md`.

---

I've drafted the spec at `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/specs/s28b-1-p2996-single-literal.md`; it is not ratified and waits for your rulings below. I ran no commands in this lane (no Bash): every command result in it comes from the two research reports and is marked `A` in PREMISES. The implementer has to resolve the new p2996 head at implementation time, preferably with `mise run p2996-refresh`, cross-checked against `gh api repos/bloomberg/clang-p2996/commits/p2996 --jq .sha`.

**What the spec does:**
- **One literal:** bake's `variable "CLANG_P2996_REF"` default is the only SHA. The Dockerfile ARG loses its default, and I wrote a replacement for its stale comment.
- **Renovate:** the new matchString is scoped to `docker-bake.hcl` only. The new packageRule goes at the end of `packageRules` so it overrides both the `image-build inputs` group rule and the generic digest auto-merge rule. I checked your field names against `renovate.json` as it is now. Both descriptions say minimumReleaseAge does nothing for git-refs.
- **`suites.toml:429`:** the token becomes `"\nARG CLANG_P2996_REF\n"`, so re-adding `=<sha>` fails the suite. No `token_audit.py` binding is affected: its only clang binding (`:188-192`) is the bake suite's token, which stays.
- **Gate:** a new pytest, `tests/test_p2996_single_literal.py`, with 8 tests. I chose it over pin-parity: pin-parity treats a site with no match as a failure, so it cannot express "no default here". Registering the Dockerfile would require the very default you ruled out. The pytest runs on every change, so the missing `docker-bake.hcl` in the `hk.pkl:583` trigger no longer matters.
- **Fail arms (§5):** re-adding the Dockerfile default, restoring the old regex, and moving the new rule above the group rule each have to turn the tests red.
- **Smoke OK line:** reworded to "(build==pin only; upstream freshness is tracked by Renovate, not checked here)". It keeps the substring `matches pinned CLANG_P2996_REF`, because `tests/test_image_smoke_exec.py:237` asserts it.
- **Upstream lag:** no new checker. An open clang Renovate PR is the lag signal, and `mise run renovate-status` already lists open update PRs.
- **Dry-run ordering:** `mise run renovate-dryrun` has to run with the new config but the old pin still in bake. After the bump there's no pending update, so it can't show the separate PR.
- **Cost:** any edit to the Dockerfile's p2996 section changes the p2996 cache key, so this PR's CI will do one cold compiler build either way.
- **Coordinator actions:** #1063 close/rebase ownership, watching the first scheduled clang PR, and updating the issues are listed separately. The spec recommends against a blanket `gitIgnoredAuthors`, because `refresh.yml:409` relies on the repair bot being an unrecognized author.

**Decisions for you:**
- **Q1** Add `test -n "${CLANG_P2996_REF}"` at the start of the clang fetch RUN? I recommend yes: it gives a clear error instead of an opaque git failure, and costs no extra cache miss. Nobody has checked what `git fetch` does with an empty ref.
- **Q2** Add `matchDatasources: ["git-refs"]` to the packageRule? The research had it, your list doesn't. I recommend leaving it out, since the dep name is unique.
- **Q3** The literal gate skips `docs/**`, `graphify-out/**` and `*.md`, because those records cite old and current SHAs. I recommend keeping that exclusion.
- **Q4** Two stale comments outside your list: `.github/workflows/refresh.yml:21-24` and `.github/workflows/AGENTS.md:18`. They become wrong once this lands. I recommend including them; that adds `pin-actions` and `lint-docs` to the checks.
- **Q5** Leave `python/pyproject.toml:36-39` unchanged? Its claim that Renovate bumps `CLANG_P2996_REF` becomes true with this change.

I added two general drafting conventions to my local memory; nothing about pending decisions went there.

## GitHub repos touched

_None._
